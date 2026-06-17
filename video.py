VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "avi", "mkv"}

def is_video_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in VIDEO_EXTENSIONS
    )
