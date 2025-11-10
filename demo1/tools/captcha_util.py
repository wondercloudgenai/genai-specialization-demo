import string
import random


class CaptchaUtil:

    @staticmethod
    def get_digit_captcha(captcha_length):
        result = ""
        for i in range(captcha_length):
            result += random.choice(string.digits)
        return result

    @staticmethod
    def get_digit_letter_captcha(captcha_length):
        result = ""
        for i in range(captcha_length):
            result += random.choice(string.ascii_letters + string.digits)
        return result


if __name__ == '__main__':
    print(CaptchaUtil.get_digit_letter_captcha(10))
