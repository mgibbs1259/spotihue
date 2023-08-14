# spotihue

# Configure

If you don't have Docker already installed, follow these [instructions](https://www.docker.com/products/docker-desktop/). Then, in the backend directory, create a copy of .example-env file and call it .env

## Hue Bridge
To find the hue bridge IP address, open your Hue app and go to settings > My Hue System > Philips Hue > i > IP-address;
Press button on top of bridge 
Then run python main.py
This only has to be done once
If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)

## Spotify API


## Fast API
docker compose up 
localhost:8000/docs

# Develop

1. Start `VS Code`
2. Open `spring`
3. Run the `Dev Containers: Open Folder in Container...` command from the Command Palette or Quick Actions Status Bar
4. Select the `Dockerfile.dev` file
5. Wait until the development container is running
6. Have fun developing!

# Thank You

-    phue
-    spotipy
