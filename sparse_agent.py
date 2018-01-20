import random

import numpy as np
import pandas as pd

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

_NO_OP = actions.FUNCTIONS.no_op.id
_SELECT_POINT = actions.FUNCTIONS.select_point.id
_BUILD_SUPPLY_DEPOT = actions.FUNCTIONS.Build_SupplyDepot_screen.id
_BUILD_BARRACKS = actions.FUNCTIONS.Build_Barracks_screen.id
_BUILD_STARPORT = actions.FUNCTIONS.Build_Starport_screen.id
_BUILD_REFINERY = actions.FUNCTIONS.Build_Refinery_screen.id
_BUILD_FACTORY = actions.FUNCTIONS.Build_Factory_screen.id
_TRAIN_MARINE = actions.FUNCTIONS.Train_Marine_quick.id
_TRAIN_MEDIC = actions.FUNCTIONS.Train_Medivac_quick.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id
_HARVEST_GATHER = actions.FUNCTIONS.Harvest_Gather_screen.id

_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
_PLAYER_ID = features.SCREEN_FEATURES.player_id.index

_PLAYER_SELF = 1
_PLAYER_HOSTILE = 4
_ARMY_SUPPLY = 5

_TERRAN_COMMANDCENTER = 18
_TERRAN_SCV = 45
_TERRAN_SUPPLY_DEPOT = 19
_TERRAN_BARRACKS = 21
_TERRAN_FACTORY = 27
_TERRAN_STARPORT = 28
_NEUTRAL_MINERAL_FIELD = 341
_NEUTRAL_VESPENE_GAS = 342

_NOT_QUEUED = [0]
_QUEUED = [1]
_SELECT_ALL = [2]

DATA_FILE = 'sparse_agent_data'

ACTION_DO_NOTHING = 'donothing'
ACTION_BUILD_SUPPLY_DEPOT = 'buildsupplydepot'
ACTION_BUILD_BARRACKS = 'buildbarracks'
ACTION_BUILD_MARINE = 'buildmarine'
ACTION_BUILD_MEDIC = 'buildmedic'
ACTION_BUILD_STARPORT = 'buildstarport'
ACTION_BUILD_FACTORY = 'buildfactory'
ACTION_BUILD_REFINERY = 'buildrefinery'
ACTION_ATTACK = 'attack'

smart_actions = [
    ACTION_DO_NOTHING,
    ACTION_BUILD_SUPPLY_DEPOT,
    ACTION_BUILD_BARRACKS,
    ACTION_BUILD_MARINE,
    ACTION_BUILD_STARPORT,
    ACTION_BUILD_FACTORY,
    ACTION_BUILD_REFINERY,
]

for mm_x in range(0, 64):
    for mm_y in range(0, 64):
        if (mm_x + 1) % 32 == 0 and (mm_y + 1) % 32 == 0:
            smart_actions.append(ACTION_ATTACK + '_' +
                                 str(mm_x - 16) + '_' + str(mm_y - 16))

# Stolen from https://github.com/MorvanZhou/Reinforcement-learning-with-tensorflow
class QLearningTable:
    def __init__(self, actions, learning_rate=0.01, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions  # a list
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon = e_greedy
        self.q_table = pd.DataFrame(columns=self.actions, dtype=np.float64)

    def choose_action(self, observation):
        self.check_state_exist(observation)

        if np.random.uniform() < self.epsilon:
            # choose best action
            state_action = self.q_table.ix[observation, :]

            # some actions have the same value
            state_action = state_action.reindex(
                np.random.permutation(state_action.index))

            action = state_action.idxmax()
        else:
            # choose random action
            action = np.random.choice(self.actions)

        return action

    def learn(self, s, a, r, s_):
        self.check_state_exist(s_)
        self.check_state_exist(s)

        q_predict = self.q_table.ix[s, a]

        if s_ != 'terminal':
            q_target = r + self.gamma * self.q_table.ix[s_, :].max()
        else:
            q_target = r  # next state is terminal

        # update
        self.q_table.ix[s, a] += self.lr * (q_target - q_predict)

    def check_state_exist(self, state):
        if state not in self.q_table.index:
            # append new state to q table
            self.q_table = self.q_table.append(
                pd.Series([0] * len(self.actions), index=self.q_table.columns, name=state))


class SparseAgent(base_agent.BaseAgent):
    def __init__(self):
        super(SparseAgent, self).__init__()

        self.qlearn = QLearningTable(actions=list(range(len(smart_actions))))
        self.previous_action = None
        self.previous_state = None
        self.cc_y = None
        self.cc_x = None
        self.move_number = 0

        #if os.path.isfile(DATA_FILE + '.gz'):
            #self.qlearn.q_table = pd.read_pickle(DATA_FILE + '.gz', compression='gzip')
    def select_workers(self, unit_type):
        unit_y, unit_x = (unit_type == _TERRAN_SCV).nonzero()
        if unit_y.any():
            i = random.randint(0, len(unit_y) - 1)
            target = [unit_x[i], unit_y[i]]
            return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])

    def build_supply_depot(self, count, obs):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        if self.move_number == 0:
            return self.select_workers(unit_type)
        elif self.move_number == 1:
            if count < 10 and _BUILD_SUPPLY_DEPOT in obs.observation['available_actions']:
                if self.cc_y.any():
                    target = self.transformDistance(round(self.cc_x.mean()), 15, round(self.cc_y.mean()), -15 + 7 * count)
                    return actions.FunctionCall(_BUILD_SUPPLY_DEPOT, [_NOT_QUEUED, target])
        elif self.move_number == 2:
            return actions.FunctionCall(_NO_OP, [])

    def build_target(self, count, obs, building_type, target):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        if self.move_number == 0:
            return self.select_workers(unit_type)
        elif self.move_number == 1:
            if count < 1 and building_type in obs.observation['available_actions']:
                if self.cc_y.any():
                    if building_type == _BUILD_FACTORY:
                        print("FAT VAGINA")
                    return actions.FunctionCall(building_type, [_NOT_QUEUED, target])
        elif self.move_number == 2:
            return actions.FunctionCall(_NO_OP, [])

    def build(self, count, obs, building_type):
        print("building {}".format(building_type))
        target = self.transformDistance(round(self.cc_x.mean()), 30, round(self.cc_y.mean()), -30 + 11.5 * count)
        return self.build_target(count, obs, building_type, target)

    @staticmethod
    def get_location(_id, obs):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        unit_y, unit_x = (unit_type == _id).nonzero()
        if unit_y.any():
            i = random.randint(0, len(unit_y) - 1)

            m_x = unit_x[i]
            m_y = unit_y[i]
            return [m_x, m_y]

    def transformDistance(self, x, x_distance, y, y_distance):
        if not self.base_top_left:
            return [x - x_distance, y - y_distance]
        return [x + x_distance, y + y_distance]

    def transformLocation(self, x, y):
        if not self.base_top_left:
            return [64 - x, 64 - y]
        return [x, y]

    def splitAction(self, action_id):
        smart_action = smart_actions[action_id]
        y = x = 0
        if '_' in smart_action:
            smart_action, x, y = smart_action.split('_')

        return (smart_action, x, y)

    def step(self, obs):
        super(SparseAgent, self).step(obs)

        if obs.last():
            reward = obs.reward

            self.qlearn.learn(str(self.previous_state),
                              self.previous_action, reward, 'terminal')

            self.qlearn.q_table.to_pickle(DATA_FILE + '.gz', 'gzip')
            self.previous_action = None
            self.previous_state = None
            self.move_number = 0

            return actions.FunctionCall(_NO_OP, [])

        unit_type = obs.observation['screen'][_UNIT_TYPE]

        if obs.first():
            player_y, player_x = (obs.observation['minimap'][_PLAYER_RELATIVE] == _PLAYER_SELF).nonzero()
            self.base_top_left = 1 if player_y.any() and player_y.mean() <= 31 else 0
            self.cc_y, self.cc_x = (unit_type == _TERRAN_COMMANDCENTER).nonzero()

        cc_y, cc_x = (unit_type == _TERRAN_COMMANDCENTER).nonzero()

        cc_count = 1 if cc_y.any() else 0

        depot_y, depot_x = (unit_type == _TERRAN_SUPPLY_DEPOT).nonzero()
        supply_depot_count = int(round(len(depot_y) / 69))

        building_types = [_TERRAN_BARRACKS, _TERRAN_STARPORT, _TERRAN_FACTORY]
        building_count = 0
        for b in building_types:
            _y, _ = (unit_type == b).nonzero()
            building_count += int(round(len(_y) / 137))

        if self.move_number == 0:
            current_state = np.zeros(8)
            current_state[0] = cc_count
            current_state[1] = supply_depot_count
            current_state[2] = building_count
            current_state[3] = obs.observation['player'][_ARMY_SUPPLY]

            if self.previous_action is not None:
                self.qlearn.learn(str(self.previous_state),
                                  self.previous_action, 0, str(current_state))

            rl_action = self.qlearn.choose_action(str(current_state))

            self.previous_state = current_state
            self.previous_action = rl_action

        smart_action, x, y = self.splitAction(self.previous_action)

        if smart_action == ACTION_BUILD_SUPPLY_DEPOT:
            move = self.build_supply_depot(supply_depot_count, obs)
        elif smart_action == ACTION_BUILD_BARRACKS:
            move = self.build(building_count, obs, _BUILD_BARRACKS)
        elif smart_action == ACTION_BUILD_REFINERY:
            target = self.get_location(_NEUTRAL_VESPENE_GAS, obs)
            move = self.build_target(building_count, obs, _BUILD_REFINERY, target)
        elif smart_action == ACTION_BUILD_STARPORT:
            move = self.build(building_count, obs, _BUILD_STARPORT)
        elif smart_action == ACTION_BUILD_FACTORY:
            move = self.build(building_count, obs, _BUILD_FACTORY)
        else:
            move = actions.FunctionCall(_NO_OP, [])
        if move is None:
            move = actions.FunctionCall(_NO_OP, [])
        
        self.move_number = 0 if self.move_number == 3 else self.move_number + 1
        return move
