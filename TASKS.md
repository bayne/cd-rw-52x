# Goal
create a simple cli tool for jumping between projects, supports only bash

# features
* automatically populate list by tracking directory history, filtering on if the directory contains a .git directory
    * store this as a .jsonl file in the standardized dot directory for unix (ie .config is for config files, so the equivalent for cache files)
* list is navigatable using arrow keys
* fuzzy-find on directory name, highlighting matching characters
* when it is not doing a match then have the list ordered by most recent
* has a `--install` command to add the hooks needed for directory history
* entries in the list contain information:
    - current git branch name or sha
    - last accessed, as relative time
* selecting the option does not immediately change directories if the TMUX is currently set as an env var (to mark that the session is currently tmux), instead it does a `tmux` send key to type it into the prompt

# Tasks
* Implement the above features, finding parallelism when possible for sub-agents
* add e2e tests and unit tests
