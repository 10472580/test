import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from typing import Union


class AESCBCPKCS7:
    """
    AES-CBC-PKCS7 加解密类（IV 必须手动指定，不自动生成）
    特性：支持 128/192/256 位密钥，手动指定 IV，Base64 编码输出，兼容中文和 Python 3.7+
    """
    def __init__(self, key: Union[str, bytes]= "==lfj123456lfj--", iv: Union[str, bytes]= "-lfj9954lfj1234l"):
        """
        初始化 AES 加密器（IV 必须传入，不可省略）
        :param key: 密钥（必须是 16/24/32 字节，对应 128/192/256 位）
                    - 若传入字符串，默认按 UTF-8 编码转为字节
        :param iv: 初始化向量（必须是 16 字节，CBC 模式强制要求）
                    - 若传入字符串，默认按 UTF-8 编码转为字节
        """
        # 处理密钥（转为字节，验证长度）
        self.key = key.encode('utf-8') if isinstance(key, str) else key
        self._validate_key_length()

        # 处理 IV（必须传入，验证长度为 16 字节）
        self.iv = iv.encode('utf-8') if isinstance(iv, str) else iv
        self._validate_iv_length()

        # 加密后端（兼容 Python 3.7+）
        self.backend = default_backend()

    def _validate_key_length(self) -> None:
        """验证密钥长度（必须是 16/24/32 字节）"""
        key_len = len(self.key)
        if key_len not in (16, 24, 32):
            raise ValueError(
                f"密钥长度必须为 16（AES-128）、24（AES-192）或 32（AES-256）字节，当前为 {key_len} 字节"
            )

    def _validate_iv_length(self) -> None:
        """验证 IV 长度（必须是 16 字节）"""
        iv_len = len(self.iv)
        if iv_len != 16:
            raise ValueError(f"IV 长度必须为 16 字节，当前为 {iv_len} 字节")

    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        加密：明文 → PKCS7 填充 → AES-CBC 加密 → 密文 → Base64 编码
        :param plaintext: 明文（字符串或字节，字符串默认按 UTF-8 编码）
        :return: 加密后的 Base64 字符串（仅含字母、数字、+、/、=）
        """
        # 处理明文（转为字节）
        plaintext_bytes = plaintext.encode('utf-8') if isinstance(plaintext, str) else plaintext

        # 初始化 PKCS7 填充器（每次加密重新创建，避免 AlreadyFinalized 错误）
        padder = padding.PKCS7(128).padder()
        padded_plaintext = padder.update(plaintext_bytes) + padder.finalize()

        # AES-CBC 加密（使用初始化时指定的 IV）
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

        # Base64 编码（无特殊字符）
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt(self, ciphertext_b64: Union[str, bytes]) -> str:
        """
        解密：Base64 解码 → 密文 → AES-CBC 解密 → PKCS7 去填充 → 明文
        :param ciphertext_b64: 加密后的 Base64 字符串（或字节）
        :return: 解密后的明文（字符串，UTF-8 编码）
        """
        # 处理密文（Base64 解码）
        try:
            ciphertext = base64.b64decode(ciphertext_b64)
        except (TypeError, ValueError) as e:
            raise ValueError(f"无效的 Base64 密文：{e}")

        # AES-CBC 解密（使用初始化时指定的 IV）
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # 初始化 PKCS7 去填充器（每次解密重新创建）
        unpadder = padding.PKCS7(128).unpadder()
        try:
            plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
        except ValueError as e:
            raise ValueError(f"解密失败（密钥错误、IV 错误、密文被篡改或填充错误）：{e}")

        # 转为字符串
        return plaintext_bytes.decode('utf-8')


# ------------------------------ 测试示例 ------------------------------
if __name__ == "__main__":
    a = AESCBCPKCS7().encrypt("lfj")
    print(a)

    print(AESCBCPKCS7().decrypt(a))