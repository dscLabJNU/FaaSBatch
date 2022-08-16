docker build --no-cache -t wc_start ~/batching-request/benchmark/wordcount/start
docker build --no-cache -t wc_count ~/batching-request/benchmark/wordcount/count
docker build --no-cache -t wc_merge ~/batching-request/benchmark/wordcount/merge