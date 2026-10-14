from auth import authenticate
from spotify_api import SpotifyClient


def main():
    access_token = authenticate()
    spotify = SpotifyClient(access_token)

    playlists = spotify.get_playlists()

    if playlists:
        print("------PLAYLISTS------")
        for playlist in playlists:
            print(
                playlist["name"],
                "-",
                playlist["tracks_total"],
                "canciones"
            )

    albums = spotify.get_saved_albums()

    if albums:
        print("------ALBUMES GUARDADOS------")
        for album in albums:
            print(
                album["name"],
                "-",
                album["artist"]
            )

    queue = spotify.get_queue()

    if queue:
        print("------COLA------")
        for item in queue:
            print(
                item["name"],
                "-",
                item["artist"]
            )


if __name__ == "__main__":
    main()