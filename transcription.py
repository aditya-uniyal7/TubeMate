from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

class Transcription:
    @staticmethod
    def get_transcription(vid):
        try:
            api = YouTubeTranscriptApi()
            tracks = api.list(vid)

            try:
                track = tracks.find_transcript(["en"])
            except Exception:
                try:
                    track = tracks.find_transcript(["hi"])
                except Exception:
                    track = next(iter(tracks))

            transcript = track.fetch()

            return " ".join(
                item["text"] for item in transcript.to_raw_data()
            )

        except Exception as e:
            print(f"Error: {e}")
            return None