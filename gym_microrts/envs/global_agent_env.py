import gym
import socket
import numpy as np
import json
from subprocess import Popen, PIPE
import os
from typing import List, Tuple
from dacite import from_dict
from gym_microrts.types import MicrortsMessage, Config
from gym import error, spaces, utils
import xml.etree.ElementTree as ET
from gym.utils import seeding
from gym_microrts.envs.base_env import BaseSingleAgentEnv

class GlobalAgentEnv(BaseSingleAgentEnv):
    """
    observation space is defined as 
    
    
    
    action space is defined as 
    
    [[0]x_coordinate(x), [1]y_coordinate(y), [2]a_t(6), [3]p_move(4), [4]p_harvest(4), 
    [5]p_return(4), [6]p_produce_direction(4), [7]p_produce_unit_type(z), 
    [8]p_attack_location_x_coordinate(x),  [9]p_attack_location_y_coordinate(y)]
    """

    def start_client(self):
        from ts import JNIClient
        from ai.rewardfunction import SimpleEvaluationRewardFunction
        rf = SimpleEvaluationRewardFunction()
        return JNIClient(rf, os.path.expanduser(self.config.microrts_path), self.config.map_path)

    def init_properties(self):
        # [num_planes_hp(5), num_planes_resources(5), num_planes_player(5), 
        # num_planes_unit_type(z), num_planes_unit_action(6)]
        self.num_planes = [5, 5, 3, len(self.utt['unitTypes'])+1, 6]
        self.observation_space = spaces.Box(low=0.0,
            high=1.0,
            shape=(self.config.height, self.config.width,
                   sum(self.num_planes)),
                   dtype=np.int32)
        self.action_space = spaces.MultiDiscrete([
            self.config.height * self.config.width,
            6, 4, 4, 4, 4,
            len(self.utt['unitTypes']),
            self.config.height * self.config.width
        ])

    def _encode_obs(self, obs: List):
        obs = obs.reshape(len(obs), -1).clip(0, np.array([self.num_planes]).T-1)
        obs_planes = np.zeros((self.config.height * self.config.width, 
                               sum(self.num_planes)), dtype=np.int)
        obs_planes[np.arange(len(obs_planes)),obs[0]] = 1

        for i in range(1, len(self.num_planes)):
            obs_planes[np.arange(len(obs_planes)),obs[i]+sum(self.num_planes[:i])] = 1
        return obs_planes.reshape(self.config.height, self.config.width, -1)

    def step(self, action, raw=False):
        raw_obs, reward, done, info = super(GlobalAgentEnv, self).step(action, True)
        # raw_obs[3] - raw_obs[4].clip(max=1) means mask busy units
        # * np.where((raw_obs[2])==2,0, (raw_obs[2]))).flatten() means mask units not owned
        self.unit_location_mask = ((raw_obs[3].clip(max=1) - raw_obs[4].clip(max=1)) * np.where((raw_obs[2])==2,0, (raw_obs[2]))).flatten()
        if raw:
            return raw_obs, reward, done, info
        return self._encode_obs(raw_obs), reward, done, info

    def reset(self, raw=False):
        raw_obs = super(GlobalAgentEnv, self).reset(True)
        self.unit_location_mask = ((raw_obs[3].clip(max=1) - raw_obs[4].clip(max=1)) * np.where((raw_obs[2])==2,0, (raw_obs[2]))).flatten()
        if raw:
            return raw_obs
        return self._encode_obs(raw_obs)

class GlobalAgentMiningEnv(GlobalAgentEnv):
    def start_client(self):
        from ts import JNIClient
        from ai.rewardfunction import ResourceGatherRewardFunction
        rf = ResourceGatherRewardFunction()
        return JNIClient(rf, os.path.expanduser(self.config.microrts_path), self.config.map_path)

class GlobalAgentBinaryEnv(GlobalAgentEnv):
    def start_client(self):
        from ts import JNIClient
        from ai.rewardfunction import WinLossRewardFunction
        rf = WinLossRewardFunction()
        return JNIClient(rf, os.path.expanduser(self.config.microrts_path), self.config.map_path)

class GlobalAgentAttackEnv(GlobalAgentEnv):
    def start_client(self):
        from ts import JNIClient
        from ai.rewardfunction import AttackRewardFunction
        rf = AttackRewardFunction()
        return JNIClient(rf, os.path.expanduser(self.config.microrts_path), self.config.map_path)

class GlobalAgentProduceWorkerEnv(GlobalAgentEnv):
    def start_client(self):
        from ts import JNIClient
        from ai.rewardfunction import ProduceWorkerRewardFunction
        rf = ProduceWorkerRewardFunction()
        return JNIClient(rf, os.path.expanduser(self.config.microrts_path), self.config.map_path)