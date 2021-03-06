#!/usr/bin/env python
# coding: utf-8

# In[34]:


from typing import List, Tuple

import pytorch_lightning as pl
from pytorch_lightning import LightningModule, Trainer
from pytorch_lightning.utilities import DistributedType
from pytorch_lightning.loggers import TensorBoardLogger

import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader
import torch.optim as optim
from torch.optim.optimizer import Optimizer
from torch.utils.data.dataset import IterableDataset
from torch.distributions import Categorical
import gym 
from gym_simplifiedtetris.envs import SimplifiedTetrisBinaryEnv as Tetris
import numpy as np

from pytorch_lightning.callbacks import Callback
import multiprocessing

from bayes_opt import BayesianOptimization
from bayes_opt.logger import JSONLogger
from bayes_opt.event import Events

from stable_baselines3.common.vec_env.dummy_vec_env import DummyVecEnv


class CriticNet(nn.Module):
    def __init__(self, obs_size, hidden_size = 100):
        super().__init__()
        
        self.critic = nn.Sequential(
            nn.Linear(obs_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1)
        )
        
    def forward(self, x):
        value = self.critic(x)
        return value

class ActorNet(nn.Module):
    def __init__(self, obs_size, n_actions, depth, hidden_size = 64):
        super().__init__()

        if depth == 2:
            self.actor = nn.Sequential(
                nn.Linear(obs_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, n_actions),
            )
        else:
            self.actor = nn.Sequential(
                nn.Linear(obs_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, n_actions),
            )

    def forward(self, x):
        #if x.sum().data.item() == 0:
            #print("ALL ZEROS INPUT : ",self.actor(x))
        logits = self.actor(x)
        logits = torch.nan_to_num(logits)
        dist = Categorical(logits=logits)
        action = dist.sample()

        return dist, action


class ActorCritic():
    def __init__(self, critic, actor):
        self.critic = critic
        self.actor = actor 
    
    @torch.no_grad()
    def __call__(self, state: torch.Tensor):
        dist, action = self.actor(state)
        probs = dist.log_prob(action)
        val = self.critic(state)
        
        return dist, action, probs, val



class RLDataSet(IterableDataset):
    def __init__(self, batch_maker):
        self.batch_maker = batch_maker
    def __iter__(self):
        return self.batch_maker()


class PPOLightning(LightningModule):
    
    def __init__(
        self,
        alr,
        clr,
        batch_size,
        clip_eps,
        lamb ,
        epoch_steps,
        gamma,
        depth,
        writer,
        envs
    ):
        self.writer = writer
        self.envs = envs
        envs = -1
        writer = -1
        super().__init__()
        self.save_hyperparameters()

        print("hparams:",self.hparams)

        self.procs = int(multiprocessing.cpu_count()/2)
        
        self.states = [[] for _ in range(self.procs)]
        for i,state in enumerate(self.envs.reset()):
            self.states[i] = torch.Tensor(state)


        print("Running",self.procs,"Environments")
        self.ep_step = 0
        self.env = Tetris(grid_dims=(10, 10), piece_size=2)
        obs_size = self.env.observation_space.shape[0]
        n_actions = self.env.action_space.n
        self.env = 0
        print("actions",n_actions)
        
        self.batch_states = [[] for _ in range(self.procs)]
        self.batch_actions = [[] for _ in range(self.procs)]
        self.batch_probs = [[] for _ in range(self.procs)]
        self.batch_advs = [[] for _ in range(self.procs)]
        self.batch_vals = [[] for _ in range(self.procs)]
        self.ep_rewards = [[] for _ in range(self.procs)]
        self.ep_vals = [[] for _ in range(self.procs)]
        self.epoch_rewards = []
        self.avg_reward = 0
        self.avg_ep_reward = 0
        
        self.critic = CriticNet(obs_size)
        self.actor = ActorNet(obs_size,n_actions,self.hparams.depth)
        
        self.agent = ActorCritic(self.critic, self.actor)
    
    def forward(self, x):
        
        dist, action = self.actor(x)
        val = self.critic(x)
        
        return dist, action, val
        
    def act_loss(self,state,action,prob_old,adv):
        dist, _ = self.actor(state.float())
        prob = dist.log_prob(action)
        ratio = torch.exp(prob - prob_old)
        #PPO update
        clip = torch.clamp(ratio, 1 - self.hparams.clip_eps, 1 + self.hparams.clip_eps) * adv
        #negative gradient descent - gradient ascent
        loss = -(torch.min(ratio * adv, clip)).mean()
        return loss
    
    def crit_loss(self,state,val):
        val_new = self.critic(state.float())
        #MSE
        loss = (val - val_new).pow(2).mean()
        return loss
        
    def compute_gae(self, rewards, values, next_val):
        

        rs = rewards
        vals = values + [next_val]
        
        x = []
        for i in range(len(rs)-1):
            x.append(rs[i]+self.hparams.gamma*vals[i+1] - vals[i])
    
        a = self.compute_reward(x, self.hparams.gamma * self.hparams.lamb)

        return a
    
    def compute_reward(self,rewards, gamma):
        
        rs = []
        sum_rs = 0

        for r in reversed(rewards):
            sum_rs = (sum_rs * gamma) + r
            rs.append(sum_rs)


        return list(reversed(rs))

    
    def make_batch(self):

        steps = int(self.hparams.batch_size * round(self.hparams.epoch_steps/self.procs/self.hparams.batch_size))
        for j in range(steps):
            #print("step",i)

            _, actions, probs, vals = self.agent(torch.stack(self.states, dim=0))

            for i,state in enumerate(self.states):               
                self.batch_states[i].append(state)
                self.batch_actions[i].append(actions[i])
                self.batch_probs[i].append(probs[i])
                self.ep_vals[i].append(vals[i].item())
            
            self.envs.step_async(actions.numpy().ravel())
            next_states, rewards, dones, _ = self.envs.step_wait()
            #print("STEPPED ",i,steps)
                
            for i, (next_state,reward) in enumerate(zip(next_states,rewards)):
                self.ep_rewards[i].append(reward)
                self.states[i] = torch.Tensor(next_state)

            
            end = j == (steps -1)

            for i, done in enumerate(dones):
                if done or end:
                    
                    if end and not done:
                        #if epoch ends before terminal state, bootstrap value
                        with torch.no_grad():
                            #print("epoch ended early")
                            _,_,_,val = self.agent(self.states[i])
                            next_val = val.item()
                    else:
                        next_val = 0
                    
                    #compute batch discounted rewards
                    self.ep_rewards[i].append(next_val)
                    self.batch_vals[i] += self.compute_reward(self.ep_rewards[i],self.hparams.gamma)[:-1]
                    self.batch_advs[i] += self.compute_gae(self.ep_rewards[i],self.ep_vals[i], next_val)
                    
                    self.epoch_rewards.append(sum(self.ep_rewards[i]))
                    print("REWARD :",sum(self.ep_rewards[i]))

                    self.ep_rewards[i].clear()
                    self.ep_vals[i].clear()

                    #env reset is not needed, SubProcVecEnv automates it. next_state is starting state
                
            if end:
                for i in range(self.procs):
                    data = zip(self.batch_states[i],
                                self.batch_actions[i],
                                self.batch_probs[i],
                                self.batch_vals[i],
                                self.batch_advs[i])

                    for (s, a, p, v, ad) in data:
                        yield s, a, p, v, ad
                    
                #logs
                    
                    self.batch_states[i].clear()
                    self.batch_actions[i].clear()
                    self.batch_probs[i].clear()
                    self.batch_vals[i].clear()
                    self.batch_advs[i].clear()

                self.avg_ep_reward = sum(self.epoch_rewards)/len(self.epoch_rewards)
                self.epoch_rewards.clear()
    
    def training_step(self, batch, batch_idx, optimizer_idx):
        
        state,action,prob_old,val,adv = batch
        # normalize adv
        adv = (adv - adv.mean())/adv.std()
        

        self.log("avg_ep_reward", self.avg_ep_reward, prog_bar=True, on_step=False, on_epoch=True, logger=True)

        
        if optimizer_idx == 0:
            loss = self.act_loss(state, action, prob_old, adv)
            self.log('act_loss', loss, on_step=False, on_epoch=True, prog_bar=True,logger=True)

            self.writer.writerow([self.global_step, self.avg_ep_reward, loss.unsqueeze(0).item()])

            return loss

        elif optimizer_idx == 1:
            loss = self.crit_loss(state,val)
            self.log('crit_loss', loss, on_step=False, on_epoch=True, prog_bar=True,logger=True)

            self.writer.writerow([self.global_step, self.avg_ep_reward, loss.unsqueeze(0).item()])

            return loss

    
    def configure_optimizers(self) -> List[Optimizer]:
        a_opt = optim.Adam(self.actor.parameters(), lr=self.hparams.alr)
        c_opt = optim.Adam(self.critic.parameters(), lr=self.hparams.clr)
        return a_opt,c_opt
    
    def __dataloader(self):
        dataset = RLDataSet(self.make_batch)
        dataloader = DataLoader(dataset=dataset, batch_size=self.hparams.batch_size)
        return dataloader
    
    def train_dataloader(self):
        return self.__dataloader()


class ReturnCallback(Callback):
    def __init__(self ):
        self.total = []

    def on_train_epoch_end(self, trainer, pl_module):
        print("Callback")
        self.total.append(trainer.callback_metrics['avg_ep_reward'].item())
    
    def get_total(self):
        return self.total

from pathlib import Path
import csv
import os

def pickFileName():

    Path("log/trainingvalsPPO/").mkdir(parents=True, exist_ok=True)

    files = os.listdir('log/trainingvalsPPO/')

    return '{}.csv'.format(len(files)+1)

def make_env():
    def thunk():
        env = Tetris(grid_dims=(10, 10), piece_size=2)
        return env
    return thunk

def train_model(alr, clr, batch_size, clip_eps, lamb, epoch_steps, depth):
    #print("entered training")    
    num_epochs=1000
    batch_size = int(batch_size)
    epoch_steps = int(epoch_steps)
    depth = int(depth)

    f = open('log/trainingvalsPPO/{}'.format(pickFileName()), 'w+')
    writer = csv.writer(f)

    procs = int(multiprocessing.cpu_count()/2)
    print("Total Core Count :",multiprocessing.cpu_count())
    
    
    envs = [make_env() for _ in range(procs)]
    envs = DummyVecEnv(envs)

    model = PPOLightning(
        alr,
        clr,
        batch_size, 
        clip_eps,
        lamb,
        epoch_steps,
        0.99, #gamma
        depth,
        writer,
        envs
    )

    tb_logger = TensorBoardLogger("log/")

    trainer = Trainer(
        gpus=0,
        max_epochs=num_epochs,
        logger=tb_logger)

    trainer.fit(model)

    print("finished training")

    f.close()
    
    totals = []

    env = Tetris(grid_dims=(10, 10), piece_size=2)
    
    with torch.no_grad():
        for i in range(10):
            done = 0
            total = 0
            step = 0
            state = env.reset()
            while not done and step < 100000:
                _,action,_ = model(torch.Tensor(state))
                state, reward, done, _ = env.step(action.item())
                total += reward
                #   print("stepped",action.item(),done)
                step +=1
            totals.append(total)
    
    print("average over final games:",np.average(totals))
    return np.average(totals)

def find_params():

    pbounds = {
        "alr" : (1e-5,1e-3),
        "clr" : (1e-5,1e-3),
        "batch_size" : (16,128),
        "clip_eps" : (0.1,0.3),
        "lamb" : (9.3e-1,9.8e-1),
        "epoch_steps" : (1024,8192),
        "depth" : (0.6,2.4)
    }
    
    optimizer = BayesianOptimization(
        f = train_model,
        pbounds=pbounds,
        random_state=1,
        verbose=1
        )

    logger = JSONLogger(path="log/logs.json")
    optimizer.subscribe(Events.OPTIMIZATION_STEP, logger)

    optimizer.maximize(
        init_points=30,
        n_iter=200,
    )

    
    print("Best hyperparameters found were: ", optimizer.max)

    print("others")
    for i, res in enumerate(optimizer.res):
       print("Iteration {}: \n\t{}".format(i, res))

if __name__ == '__main__':
    print("Starting...")
    find_params()

#model = PPOLightning().load_from_checkpoint("/home/scrungus/Documents/dissertation/Tetris/gym-simplifiedtetris/log/default/version_3/checkpoints/epoch=58-step=11799.ckpt")
""" print("Playing")
env = gym.make("simplifiedtetris-binary-10x10-2-v0")    
state = env.reset()

done = 0
while not done:
    _,action,_ = model(torch.Tensor(state))
    state, _, done, _ = env.step(action.item())
    env.render() """
