import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def test_logging():
    logging.info('这是一个info日志测试')
    logging.error('这是一个error日志测试')
    print('这是一个print测试')

if __name__ == '__main__':
    test_logging() 