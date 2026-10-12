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