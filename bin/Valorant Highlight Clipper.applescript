set appPath to POSIX path of (path to me)
set shellCommand to "APP_PATH=" & quoted form of appPath & "; PROJECT_DIR=$(cd \"$(dirname \"$APP_PATH\")/..\" && pwd); cd \"$PROJECT_DIR\" && './bin/valorant_clipper.command'"
tell application "Terminal"
  do script shellCommand
  activate
end tell
