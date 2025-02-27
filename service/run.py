# main.py
import argparse
from fastapi import FastAPI

app = FastAPI()


def include_service(service_name: str):
    """
    Load the corresponding route module according to service_name and register it to app
    根据 service_name 加载对应的路由模块并注册到 app 上
    """
    if not service_name:
        raise ValueError(
            "Please specify the name of the service to load\n请指定要加载的服务名称"
        )
    elif service_name == "user":
        from user import router as user_router

        app.include_router(user_router)
    else:
        raise ValueError(
            f"Unknown service name: {service_name}\n未知的服务名称: {service_name}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Start the specified service\n启动指定服务"
    )
    parser.add_argument(
        "--service",
        type=str,
        default=None,
        help="Specify the name of the service to run, for example: user, problem\n指定要运行的 service 名称，例如：user, problem",
    )
    args = parser.parse_args()

    try:
        include_service(args.service)
    except ValueError as e:
        print(e)
        exit(1)

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
