from model import SessionLocal, AdminUserModel
from services.service_user import UserService


def init_admin_user():
    with SessionLocal() as session:
        try:
            model = AdminUserModel(account="admin", password=UserService.get_password_hash("12345qwe"), is_super=True)
            session.add(model)
        except Exception as e:
            print(f"异常：{e}")
        session.commit()
    print("添加 admin 超管账号成功")


if __name__ == "__main__":
    init_admin_user()
