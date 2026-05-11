set appPath to POSIX path of (path to me)
do shell script "APP_PATH=" & quoted form of appPath & "; PROJECT_DIR=$(cd \"$(dirname \"$APP_PATH\")/..\" && pwd); cd \"$PROJECT_DIR\" && './bin/valorant_clipper_control.command'"
