<h1 align="center"> Gym-SimplifiedTetris </h1> <br>

<p align="center">
    <img src="assets/20x10_4_heuristic.gif" width="400">
</p>


## Table of contents <!-- omit in toc -->

- [1. Introduction](#1-introduction)
- [2. Getting started](#2-getting-started)
- [3. Environments](#3-environments)
  - [3.1. Available environments](#31-available-environments)
  - [3.2. Building more environments](#32-building-more-environments)
  - [3.3. Methods](#33-methods)
    - [3.3.1. `reset()` method](#331-reset-method)
    - [3.3.2. `step(action: int)` method](#332-stepaction-int-method)
    - [3.3.3. `render()` method](#333-render-method)
    - [3.3.4. `close()` method](#334-close-method)
  - [3.4. Variable dimensions and piece size](#34-variable-dimensions-and-piece-size)
  - [3.5. Action and observation spaces](#35-action-and-observation-spaces)
  - [3.6. Game ending](#36-game-ending)
  - [3.7. Usage](#37-usage)
- [4. Agents](#4-agents)
  - [4.1. Uniform](#41-uniform)
  - [4.2. Q-learning](#42-q-learning)
  - [4.3. Heuristic](#43-heuristic)
- [5. Future work](#5-future-work)
- [6. How to contribute](#6-how-to-contribute)
- [7. Acknowledgements](#7-acknowledgements)
- [8. Citing the project](#8-citing-the-project)
- [9. License](#9-license)

## 1. Introduction

<p align="left">
  <a href="https://www.codefactor.io/repository/github/oliveroverend/gym-simplifiedtetristemp">
    <img src="https://www.codefactor.io/repository/github/oliveroverend/gym-simplifiedtetristemp/badge">
  </a>
  <a href="/LICENSE.md">
    <img src="https://img.shields.io/github/license/OliverOverend/gym-simplifiedtetristemp?color=red">
  </a>
  <a href="https://github.com/OliverOverend/gym-simplifiedtetristemp/compare">
    <img src="https://img.shields.io/badge/PRs-welcome-success.svg?style=flat">
  </a>
  <a href="https://github.com/OliverOverend/gym-simplifiedtetristemp/issues/new/choose">
    <img src="https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat">
  </a>
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg">
  </a>
</p>

Gym-SimplifiedTetris is a Python package that can create *simplified* reinforcement learning (RL) environments for Tetris, which conform to the [OpenAI Gym](https://github.com/openai/gym) API. The environments are simplified because the artificial agent must select the column and piece's rotation before the piece is dropped vertically downwards. If one looks at the previous approaches to the game of Tetris, most of them use this simplified setting.

This README provides some help with the setup, gives an overview of the environments and how to use them, and describes how to build more environments.

## 2. Getting started

If you would like to contribute, I'd recommend following [this](https://thenewstack.io/getting-legit-with-git-and-github-your-first-pull-request/) advice. In summary, fork the repo :arrow_right: clone it :arrow_right: create a new branch :arrow_right: make changes :arrow_right: merge to master :arrow_right: create a new pull request [here](https://github.com/OliverOverend/gym-simplifiedtetristemp/compare).

Or, you can clone the repository to create a local copy on your machine:

```bash
git clone https://github.com/OliverOverend/gym-simplifiedtetristemp
```

Here is a list of the versions used throughout development:

- Python==3.7.4
- NumPy==1.16.5
- Gym==0.18.0
- OpenCV-Python==4.5.1
- Imageio==2.6.0
- Matplotlib==3.4.2
- Pillow==6.2.0
- Stable-Baselines3==1.1.0

## 3. Environments

### 3.1. Available environments

There are currently two environments provided:

- `simplifiedtetris-binary-v0`: The observation space is a flattened NumPy array containing a binary representation of the grid, plus the current piece's ID
- `simplifiedtetris-partbinary-v0`: The observation space is a flattened NumPy array containing a binary representation of the grid excluding the top `piece_size` rows, plus the current piece's ID

### 3.2. Building more environments

The user can implement more custom Gym environments with different observation spaces and reward functions easily. To add more environments to `gym_simplifiedtetris.register.env_list`, ensure that they inherit from `SimplifiedTetrisBinaryEnv` and are registered using:

```python
>>> register(
>>>     idx='INSERT_ENV_NAME_HERE',
>>>     entry_point='gym_simplifiedtetris.envs:INSERT_ENV_CLASS_NAME_HERE',
>>> )
```

### 3.3. Methods

#### 3.3.1. `reset()` method

The `reset()` method returns a 1D array containing some grid binary representation, plus the current piece's ID.

```python
>>> obs = env.reset()
>>> print(obs)
[0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
 0 0 0 0 0 0 0 0 0 0 0 0 4]
```

#### 3.3.2. `step(action: int)` method

Each environment's step method returns four values:

- `observation` (**NumPy array**): a 1D array that contains some binary representation of the grid, plus the current piece's ID
- `reward` (**float**): the amount of reward received from the previous action
- `done` (**bool**): a game termination flag
- `info` (**dict**): only contains the `num_rows_cleared` due to taking the previous action

```python
>>> obs, rwd, done, info = env.step(action)
```

#### 3.3.3. `render()` method

The user has access to the following controls during rendering:

- Pause (**SPACEBAR**)
- Speed up (**RIGHT key**)
- Slow down (**LEFT key**)
- Quit (**ESC**)

```python
>>> env.render()
```

#### 3.3.4. `close()` method

The user can close all open windows using:

```python
>>> env.close()
```

### 3.4. Variable dimensions and piece size

The user can deviate from the standard grid dimensions and Tetriminos by editing the `gym_register` keyword arguments. The user can choose from four different sets of pieces: monominos, dominos, trominoes & Tetriminos. The user can select a height in the interval [`piece_size`+1, 20] and a width in the interval [`piece_size`, 10]. Below is a GIF showing games being played on a 8 x 6 grid with trominoes as the pieces.

<p align="center">
    <img src="assets/8x6_3.gif" width="400">
</p>

### 3.5. Action and observation spaces

Each environment comes with an `observation_space` that is a `Box` space and an `action_space` that is a `Discrete` space. At each time step, the artificial agent must choose an action (an integer from a particular range). Each action maps to a translation/rotation tuple that specifies the column to drop the piece and its rotation. The ranges for the four different piece sizes are:

- Monominos: [0, w - 1]
- Dominos: [0, 2w - 2]
- Trominoes: [0, 4w - 5]
- Tetriminos: [0, 4w  - 7]

where w is the grid width.

### 3.6. Game ending

Each game of Tetris terminates if the following condition is satisfied: any of the dropped piece's square blocks enter into the top `piece_size` rows before any full rows are cleared. This definition ensures that scores achieved are lower bounds on the score that the agent could have obtained on a standard game of Tetris, as laid out in Colin Fahey's ['Standard Tetris' specification](https://www.colinfahey.com/tetris/tetris.html#:~:text=5.%20%22Standard%20Tetris%22%20specification).

### 3.7. Usage

The file [example.py](https://github.com/OliverOverend/gym-simplifiedtetristemp/blob/master/example.py) shows an example of using an instance of the `simplifiedtetris-binary-v0` environment for ten games:

```python
import gym

import gym_simplifiedtetris

env = gym.make('simplifiedtetris-binary-v0')
obs = env.reset()

# Run 10 games of Tetris, selecting actions uniformly at random.
num_episodes = 0
while num_episodes < 10:
    env.render()
    action = env.action_space.sample()
    obs, rwd, done, info = env.step(action)

    if done:
        print(f"Episode {num_episodes + 1} has terminated.")
        num_episodes += 1
        obs = env.reset()

env.close()
```

Alternatively, the environment can be imported directly:

```python
from gym_simplifiedtetris.envs import SimplifiedTetrisBinaryEnv as Tetris

env = Tetris(
    grid_dims=(20, 10),
    piece_size=4,
)
```

## 4. Agents

Three agents are currently available:

- [Uniform](#41-uniform)
- [Q-learning](#42-q-learning)
- [Heuristic](#43-heuristic)

### 4.1. Uniform

The uniform agent implemented by `gym_simplifiedtetris.UniformAgent` selects actions uniformly at random. See [run_uniform.py](https://github.com/OliverOverend/gym-simplifiedtetristemp/blob/master/run_uniform.py) for an example of how to use the uniform agent.

<p align="center">
    <img src="assets/20x10_4.gif" width="450">
</p>

### 4.2. Q-learning

The Q-learning agent implemented by `gym_simplifiedtetris.QLearningAgent` selects the action with the highest Q-value (state-action value). Note that this agent struggles to learn as the grid's dimensions are increased (the size of the state-action space becomes too large).

See [run_q_learning.py](https://github.com/OliverOverend/gym-simplifiedtetristemp/blob/master/run_q_learning.py) for an example of how to use the Q-learning agent.

<p align="center">
    <img src="assets/7x4_3_q_learning.gif" width="400">
</p>

### 4.3. Heuristic

The heuristic agent implemented by `gym_simplifiedtetris.DellacherieAgent` selects the action with the highest heuristic score, which is based on the [Dellacherie feature set](https://arxiv.org/abs/1905.01652). 

The heuristic score for each possible action is computed using the following heuristic:

***- landing height + eroded cells - row transitions - column transitions -4 x holes - cumulative wells***

See [run_heuristic.py](https://github.com/OliverOverend/gym-simplifiedtetristemp/blob/master/run_heuristic.py) for an example of how to use the heuristic agent.

<p align="center">
    <img src="assets/20x10_4_heuristic.gif" width="400">
</p>

## 5. Future work

- [ ] Unit tests:
  - [X] Tetriminos
  - [ ] Trominoes
  - [ ] Dominos
  - [ ] Monominos
  - [X] Heuristic
- [X] Agents:
  - [X] Q-learning
  - [X] Uniform
  - [X] Heuristic (Dellacherie feature set)
- [ ] Environments with alternative:
  - [ ] Observation spaces (normalised)
  - [ ] Reward functions (shaping rewards)
  - [ ] Action spaces (non-terminal actions only)

## 6. How to contribute

Please feel free to provide any suggestions [here](https://github.com/OliverOverend/gym-simplifiedtetristemp/discussions/new). Please report any bugs [here](https://github.com/OliverOverend/gym-simplifiedtetristemp/issues/new?assignees=OliverOverend&labels=bug&template=BUG_REPORT.md&title=%5BBUG%5D%3A) or create a feature request [here](https://github.com/OliverOverend/gym-simplifiedtetristemp/issues/new?assignees=OliverOverend&labels=enhancement&template=FEATURE_REQUEST.md&title=%5BFEATURE%5D%3A). Pull requests can be created [here](https://github.com/OliverOverend/gym-simplifiedtetristemp/compare).

## 7. Acknowledgements

This package utilises several methods from the [codebase](https://github.com/andreanlay/tetris-ai-deep-reinforcement-learning) developed by andreanlay (2020). The class hierarchy design was inspired by a [codebase](https://github.com/Hewiiitt/Gym-Circuitboard) developed by Hewiiitt.

## 8. Citing the project

```
@misc{gym_simplifiedtetris,
  author = {Overend, Oliver},
  title = {gym-simplifiedtetris package for OpenAI Gym},
  year = {2021},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/OliverOverend/gym-simplifiedtetristemp}},
}
```

## 9. License

This project is licensed under the terms of the [MIT license](/LICENSE.md).
