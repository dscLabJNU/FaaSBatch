docker build --no-cache -t video_upload ~/batching-request/benchmark/video/upload
docker build --no-cache -t video_simple_process ~/batching-request/benchmark/video/simple_process
docker build --no-cache -t video_split ~/batching-request/benchmark/video/split
docker build --no-cache -t video_transcode ~/batching-request/benchmark/video/transcode
docker build --no-cache -t video_merge ~/batching-request/benchmark/video/merge