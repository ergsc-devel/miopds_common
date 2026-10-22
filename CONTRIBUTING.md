# Misc. info. for developers working with this repository


## Git branches and their policies
The main branch is `main`. The primary branch for the development task is `devel`. 
### the `main` branch
* No one is allowed to push any changes directly to the `main` branch.
* Any changes in `main` branch must go through the pull request process from the `devel` branch.
### the `devel` branch
* The `devel` branch is the primary branch for the development task.
* Any changes in `devel` branch should be tested before merging to `main`.
* It is strongly recommeneded to use pull request process even in the `devel` branch.
* Developers can directly push a change to this branch if 1) the change is very minor and 2) affects only a very limited part of the code in this repository and 3) the change is formed with only 1-2 commits.

### the `enh_*` branch
* The `enh_*` branches are used for the development of new features. 
* Any changes in these branches should be tested before merging to `devel`.










