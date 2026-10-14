import requests

class SpotifyClient:
    def __init__(self, access_token):
        self.access_token = access_token

    def pause(self):
        url = "https://api.spotify.com/v1/me/player/pause"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.put(url, headers=headers)
        return response

    def play(self):
        url = "https://api.spotify.com/v1/me/player/play"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.put(url, headers=headers)
        return response           

    def next(self):
        url = "https://api.spotify.com/v1/me/player/next"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.post(url, headers=headers)
        return response

    def previous(self):
        url = "https://api.spotify.com/v1/me/player/previous"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.post(url, headers=headers)
        return response

    def set_volume(self, volume_percent):
        url = "https://api.spotify.com/v1/me/player/volume"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "volume_percent": volume_percent
        }        
        if 0 <= volume_percent <= 100:
            response = requests.put(url, headers=headers, params=params)
            return response
        else:
            raise ValueError("El volumen debe estar entre 0 y 100.")

    def get_current_track(self):
        url = "https://api.spotify.com/v1/me/player/currently-playing"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }        
        response = requests.get(url, headers=headers)
        return response

    def search_tracks(self, query):
        url = "https://api.spotify.com/v1/search"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "q": query,
            "type": "track",
            "limit": 5
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            tracks = data["tracks"]["items"]

            songs = []

            for track in tracks:
                song = {
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "album": track["album"]["name"],
                    "image": track["album"]["images"][0]["url"],
                    "uri": track["uri"]
                }
                songs.append(song)
            return songs        

    def play_track(self, track_uri):
        url = "https://api.spotify.com/v1/me/player/play"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        data = {
            "uris": [track_uri]
        }
        
        response = requests.put(
            url,
            headers=headers,
            json=data
        )

        return response

    def get_playlists(self):
        url = "https://api.spotify.com/v1/me/playlists"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        params = {
            "limit": 50
        }

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            playlists_data = data["items"]

            playlists = []

            for playlist_data in playlists_data:
                if playlist_data["images"]:
                    image = playlist_data["images"][0]["url"]
                else:
                    image = None

                playlist = {
                    "name": playlist_data["name"],
                    "id": playlist_data["id"],
                    "image": image,
                    "tracks_total": playlist_data["items"]["total"]
                }
                
                playlists.append(playlist)

            return playlists

        else:
            return None

    def get_saved_albums(self):
        url = "https://api.spotify.com/v1/me/albums"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        params = {
            "limit": 50
        }

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            albums_data = data["items"]

            albums = []

            for item in albums_data:
                album_data = item["album"]

                if album_data["images"]:
                    image = album_data["images"][0]["url"]
                else:
                    image = None

                album = {
                    "name": album_data["name"],
                    "artist": album_data["artists"][0]["name"],
                    "image": image,
                    "id": album_data["id"],
                    "tracks_total": album_data["total_tracks"]
                }

                albums.append(album)

            return albums

        else:
            return None

    def get_queue(self):
        url = "https://api.spotify.com/v1/me/player/queue"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            queue_data = data["queue"]

            queue = []

            for item in queue_data:

                if item["type"] != "track":
                    continue

                if item["album"]["images"]:
                    image = item["album"]["images"][0]["url"]
                else:
                    image = None

                song = {
                    "name": item["name"],
                    "artist": item["artists"][0]["name"],
                    "album": item["album"]["name"],
                    "image": image,
                    "uri": item["uri"]
                }

                queue.append(song)

            return queue

        else:
            return None