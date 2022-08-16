docker build --no-cache -t recognizer_upload ~/batching-request/benchmark/illgal_recognizer/upload
docker build --no-cache -t recognizer_adult ~/batching-request/benchmark/illgal_recognizer/adult_detector
docker build --no-cache -t recognizer_violence ~/batching-request/benchmark/illgal_recognizer/violence_detector
docker build --no-cache -t recognizer_mosaic ~/batching-request/benchmark/illgal_recognizer/mosaic
docker build --no-cache -t recognizer_extract ~/batching-request/benchmark/illgal_recognizer/extract
docker build --no-cache -t recognizer_translate ~/batching-request/benchmark/illgal_recognizer/translate
docker build --no-cache -t recognizer_word_censor ~/batching-request/benchmark/illgal_recognizer/word_censor