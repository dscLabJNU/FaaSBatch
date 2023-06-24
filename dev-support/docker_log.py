import docker
docker_client = docker.from_env()
cnt = 0
containers = docker_client.containers.list(filters={"label": "workflow"})
for c in containers:
    logs = c.logs().decode("utf-8")
    print(logs, file=open("./docker.log", "a"))
    if "Error" in logs:
        print(logs)
        # break