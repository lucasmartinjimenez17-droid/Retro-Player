from auth import authenticate
from spotify_api import SpotifyClient

def main():
    access_token = authenticate()
    spotify = SpotifyClient(access_token)
    songs = spotify.search_tracks("Kanye West")

    if songs:
        for song in songs:
            print(song["name"], "-", song["artist"])


if __name__ == "__main__":
    main()