# AstraFin source submission / 源码提交

GitHub为源码权威来源。首版提交分支为 `codex/astrafin-v0.1.0`，通过PR审查；分支代码不代表已合并main或已部署。实际CI结果见该提交及PR的Checks。
GitHub is the source of truth. The initial submission uses `codex/astrafin-v0.1.0` and a review PR. A branch submission is not a main-branch merge or deployment. Consult the commit and PR checks for actual CI results.

源码分支 / Source branch: https://github.com/accentgrove/AstraFin/tree/codex/astrafin-v0.1.0

日常开发从GitHub克隆并在新分支修改；以下脚本仅用于首次导入，检测到已有应用文件时会停止。
For ongoing development, clone GitHub and work on a new branch. The script below is for initial import only and stops if application files already exist.

本包仅含公开源码和脱敏规格，无真实账户余额、交易数据库或访问令牌。原来的私人首版与本地账本没有被改写。
This package contains public source and a sanitized specification, without actual balances, trading databases or access tokens. The earlier private build and local ledger are unchanged.

在装有Git和Python 3.12+的电脑解压。先通过Git自己的正常登录方式授权；不要把令牌放在文件或聊天中。然后运行：
Extract on a computer with Git and Python 3.12+. Authenticate through Git's normal local flow; do not put tokens in files or chat. Then run:

```sh
python3 publish_to_github.py --push
```

Windows可使用 `py -3 publish_to_github.py --push`。
On Windows, use `py -3 publish_to_github.py --push`.

脚本克隆AstraFin、创建独立分支、检查现有文件、合并原有.gitignore、运行测试并推送该分支。不会合并main；遇到新的同名文件会停止，保留原文件。
The script clones AstraFin, creates a separate branch, checks for existing files, merges the original .gitignore, runs tests and pushes that branch. It never merges main and stops rather than overwriting new conflicting files.

若只希望在电脑上准备并检查，不推送：
To prepare and inspect locally without pushing:

```sh
python3 publish_to_github.py
```

推送完成后，在GitHub创建PR。若Git提示没有权限，需使用对该仓库有Contents写入及提交工作流文件权限的登录。
After pushing, open a PR on GitHub. If Git reports insufficient permission, use an identity with repository Contents write access and permission to submit workflow files.
