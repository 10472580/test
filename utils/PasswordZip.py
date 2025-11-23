import os
import shutil
import pyzipper
from typing import Union, List


class PasswordZip:
    """
    跨平台带密码 ZIP 压缩/解压类（兼容 Windows/Linux）
    加密算法：AES-256（Windows 资源管理器、Linux unzip 均支持）
    """

    def __init__(self, password: str):
        """
        初始化密码（转为字节类型，兼容 pyzipper 要求）
        :param password: 压缩/解压密码（字符串）
        """
        self.password = password.encode('utf-8')  # 密码必须是字节类型

    def _get_files_to_compress(self, source: Union[str, List[str]]) -> List[str]:
        """
        获取待压缩的所有文件路径（支持单个文件或目录，递归处理子目录）
        :param source: 单个文件路径、目录路径，或文件/目录列表
        :return: 所有待压缩文件的绝对路径列表
        """
        files = []
        # 处理输入为列表的情况
        sources = [source] if isinstance(source, str) else source

        for s in sources:
            s_abs = os.path.abspath(s)
            if not os.path.exists(s_abs):
                print(f"警告：路径不存在，跳过 → {s_abs}")
                continue

            if os.path.isfile(s_abs):
                # 单个文件直接加入
                files.append(s_abs)
            elif os.path.isdir(s_abs):
                # 目录：递归遍历所有文件
                for root, _, filenames in os.walk(s_abs):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        files.append(file_path)
        return files

    def compress(
            self,
            source: Union[str, List[str]],
            zip_filename: str,
            include_parent_dir: bool = False,
            compress_level: int = 6,
            delete_srouce: bool = False
    ) -> None:
        """
        带密码压缩文件/目录
        :param source: 待压缩的文件路径、目录路径，或文件/目录列表
        :param zip_filename: 输出的 ZIP 文件名（如 "output.zip"）
        :param include_parent_dir: 压缩目录时是否包含父目录（True=保留目录结构，False=仅保留文件）
        :param compress_level: 压缩级别（0=无压缩，1=最快，9=最优，默认 6）
        """
        # 获取所有待压缩文件
        files_to_compress = self._get_files_to_compress(source)
        if not files_to_compress:
            raise ValueError("没有找到可压缩的文件或目录")

        # 初始化 AES-256 加密的 ZIP 文件
        with pyzipper.AESZipFile(
                zip_filename,
                'w',
                compression=pyzipper.ZIP_DEFLATED,
                compresslevel=compress_level,
                encryption=pyzipper.WZ_AES  # 必须指定 AES 加密（跨平台兼容）
        ) as zipf:
            # 设置密码
            zipf.setpassword(self.password)

            # 遍历文件并添加到 ZIP
            for file_path in files_to_compress:
                # 计算 ZIP 内部的相对路径（保留目录结构）
                if include_parent_dir:
                    # 保留完整的相对路径（如 "dir/subdir/file.txt"）
                    arcname = os.path.relpath(file_path, os.path.dirname(os.path.commonprefix(files_to_compress)))
                else:
                    # 仅保留文件名（如 "file.txt"，忽略目录结构）
                    arcname = os.path.basename(file_path)

                # 添加文件到 ZIP
                zipf.write(file_path, arcname=arcname)
                print(f"已添加 → {file_path} → ZIP 内部路径：{arcname}")

        print(f"\n✅ 压缩完成！ZIP 文件：{os.path.abspath(zip_filename)}")
        if delete_srouce:
            shutil.rmtree(source)

    def extract(
            self,
            zip_filename: str,
            extract_dir: str = "extracted_files",
            overwrite: bool = False
    ) -> None:
        """
        带密码解压 ZIP 文件
        :param zip_filename: 待解压的 ZIP 文件名
        :param extract_dir: 解压目录（默认 "extracted_files"，不存在则自动创建）
        :param overwrite: 是否覆盖已存在的文件（True=覆盖，False=跳过）
        """
        # 检查 ZIP 文件是否存在
        if not os.path.exists(zip_filename):
            raise FileNotFoundError(f"ZIP 文件不存在 → {zip_filename}")

        # 创建解压目录
        os.makedirs(extract_dir, exist_ok=True)

        # 读取加密 ZIP 文件
        with pyzipper.AESZipFile(zip_filename, 'r') as zipf:
            # 验证密码（可选，提前校验避免解压失败）
            try:
                zipf.setpassword(self.password)
                # 尝试读取文件列表（密码错误会抛出异常）
                zipf.namelist()
            except RuntimeError as e:
                raise ValueError(f"密码错误或 ZIP 文件损坏：{e}")

            # 解压所有文件
            for file_info in zipf.infolist():
                file_name = file_info.filename
                extract_path = os.path.join(extract_dir, file_name)

                # 处理覆盖逻辑
                if os.path.exists(extract_path) and not overwrite:
                    print(f"跳过（已存在）→ {extract_path}")
                    continue

                # 解压文件（保留目录结构）
                with zipf.open(file_info) as source, open(extract_path, 'wb') as target:
                    target.write(source.read())
                print(f"已解压 → {file_name} → {extract_path}")

        print(f"\n✅ 解压完成！解压目录：{os.path.abspath(extract_dir)}")


# ------------------------------ 测试示例 ------------------------------
if __name__ == "__main__":
    # 初始化密码（建议使用复杂密码，避免弱密码）
    zip_password = "MySecurePassword123!"

    # 创建压缩/解压实例
    pzip = PasswordZip(password=zip_password)

    # ------------------------------ 测试压缩 ------------------------------
    print("=== 开始压缩测试 ===")
    # 待压缩的内容（可替换为你的文件/目录路径）
    test_source = [
        "test_file.txt",  # 单个文件
        "test_directory"  # 目录（会递归压缩子文件）
    ]
    # 执行压缩（保留目录结构，压缩级别 6）
    pzip.compress(
        source=test_source,
        zip_filename="encrypted_files.zip",
        include_parent_dir=True,
        compress_level=6
    )

    # ------------------------------ 测试解压 ------------------------------
    print("\n=== 开始解压测试 ===")
    # 执行解压（解压到默认目录，允许覆盖）
    pzip.extract(
        zip_filename="encrypted_files.zip",
        extract_dir="my_extracted_files",
        overwrite=True
    )

    # ------------------------------ 跨平台验证说明 ------------------------------
    print("\n=== 跨平台兼容说明 ===")
    print("1. Windows：直接右键解压，输入密码即可（支持 AES-256）")
    print("2. Linux：使用命令解压 → unzip encrypted_files.zip（输入密码即可）")
    print("3. 若 Linux unzip 版本过低，需升级：sudo apt update && sudo apt install unzip")
