import subprocess
subprocess.call(['git', 'add', 'test.md'], cwd="../../docs-slackbot.wiki")
subprocess.call(['git', 'commit', '-am', "commit"], cwd="../../docs-slackbot.wiki")
subprocess.call(['git', 'push'], cwd="../../docs-slackbot.wiki")