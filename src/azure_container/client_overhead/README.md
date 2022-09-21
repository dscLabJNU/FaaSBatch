1. `bash build_images.sh` for building docker images

2. Enter `test` folder, and run 
```shell
python eval_container.py --mode native # run evaluation in container in native mode
python eval_container.py --mode optimize # run evaluation in container in optimize mode

python eval_host.py --mode native # run evaluation in host in native mode
python eval_host.py --mode optimize # run evaluation in host in optimize mode
```

3. The results will be stored in `logs` folder