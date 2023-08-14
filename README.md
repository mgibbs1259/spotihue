# spotihue

# Configure

If you don't have Docker already installed, follow these [instructions](https://www.docker.com/products/docker-desktop/). Then, in the backend directory, create a copy of .example-env file and call it .env

## Hue Bridge IP
To find the Hue Bridge IP address, open your Hue app and go to Settings > My Hue System > Philips Hue > i > IP-address. 
Set the HUE_BRIDGE_IP_ADDRESS variable to the Hue Bridge IP address in the .env file.

## Spotify API
To find the necessary Spotify API credentials, follow the steps below.

1) Log into [Spotify for Developers](https://developer.spotify.com/) using your Spotify account
2) Create an app called spotihue, which will enable you to have access to the Spotify API credentials
3) Go to your [Dashboard](https://developer.spotify.com/dashboard) > spotihue > Settings
4) Under Basic Information, ensure that the App Name is spotihue and that the Redirect URIs is `http://localhost:8888/callback/`
5) Obtain your Username, Client ID, and Client Secret.

Set the SPOTIFY_USERNAME, SPOTIFY_CLIENT_ID, and SPOTIFY_CLIENT_SECRET variables using the Spotify API credentials in the .env file.

For additional information on the Spotify API, look [here](https://developer.spotify.com/documentation/web-api).

# Run
1) `docker compose up`
2) Press and hold button on top of Hue Bridge for about 3 seconds
3) Go to `localhost:8000/docs` to interact with the spotihue API

# Develop

1. Start `VS Code`
2. Open `spring`
3. Run the `Dev Containers: Open Folder in Container...` command from the Command Palette or Quick Actions Status Bar
4. Select the `Dockerfile.dev` file
5. Wait until the development container is running
6. Have fun developing!

# Thank You

-    studioimaginaire - for phue
-    spotipy-dev - for spotipy
-    hcannan for your advice