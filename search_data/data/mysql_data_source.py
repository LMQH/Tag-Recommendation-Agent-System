# -*- coding: utf-8 -*-
"""
MySQL数据源连接类
用于连接b2b预演库并查询相关表数据
"""
import pymysql
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager


class B2BMySQLDataSource:
    """b2b预演库MySQL数据源连接类"""
    
    def __init__(self, host: str = "121.41.50.245", port: int = 3306,
                 user: str = "shaoshuai", password: str = "jlS2DT6pmh7KLBdgbZsE",
                 charset: str = "utf8mb4"):
        """
        初始化数据库连接参数
        
        参数:
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            charset: 字符集
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.charset = charset
        self.connection: Optional[pymysql.Connection] = None
        
    def connect(self, database: Optional[str] = None) -> pymysql.Connection:
        """
        建立数据库连接
        
        参数:
            database: 数据库名称（可选，如果不指定则不选择特定数据库）
        
        返回:
            pymysql.Connection 对象
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,  # 返回字典格式的结果
                connect_timeout=10,  # 连接超时时间（秒）
                read_timeout=30,  # 读取超时时间（秒）
                write_timeout=30,  # 写入超时时间（秒）
                autocommit=True  # 自动提交
            )
            logging.info(f"成功连接到数据库 {self.host}:{self.port}")
            return self.connection
        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logging.info("数据库连接已关闭")
    
    @contextmanager
    def get_connection(self, database: Optional[str] = None):
        """
        上下文管理器，自动管理数据库连接的创建和关闭
        
        参数:
            database: 数据库名称（可选）
        
        使用示例:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM skycrane_website.t_trim_festival_data LIMIT 10")
                results = cursor.fetchall()
        """
        conn = None
        try:
            conn = self.connect(database)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        执行查询语句并返回结果（支持跨数据库查询，带重试机制）
        
        参数:
            query: SQL查询语句（可以使用 database.table 格式）
            params: 查询参数（可选）
            max_retries: 最大重试次数，默认3次
            
        返回:
            查询结果列表（字典格式）
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    try:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                        results = cursor.fetchall()
                        logging.info(f"查询执行成功，返回 {len(results)} 条记录")
                        return results
                    except Exception as e:
                        logging.error(f"查询执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        last_exception = e
                        raise
                    finally:
                        cursor.close()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logging.warning(f"查询失败，{1}秒后重试...")
                    import time
                    time.sleep(1)
                else:
                    logging.error(f"查询执行失败，已重试 {max_retries} 次: {e}")
                    raise last_exception
        raise last_exception
    
    def get_festival_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取节日数据表数据
        
        参数:
            limit: 限制返回的记录数，默认1000
            
        返回:
            节日数据列表
        """
        query = f"""
        SELECT *
        FROM skycrane_website.t_trim_festival_data
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_festival_count(self) -> int:
        """
        获取节日数据表总数
        
        返回:
            记录总数
        """
        query = """
        SELECT COUNT(1) as total
        FROM skycrane_website.t_trim_festival_data
        """
        result = self.execute_query(query)
        return result[0]['total'] if result else 0
    
    def get_brand_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取品牌数据表数据
        
        参数:
            limit: 限制返回的记录数，默认1000
            
        返回:
            品牌数据列表
        """
        query = f"""
        SELECT *
        FROM skycrane_goods.t_brand
        WHERE is_deleted = 0
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_brand_count(self) -> int:
        """
        获取品牌数据表总数
        
        返回:
            记录总数
        """
        query = """
        SELECT COUNT(1) as total
        FROM skycrane_goods.t_brand
        WHERE is_deleted = 0
        """
        result = self.execute_query(query)
        return result[0]['total'] if result else 0
    
    def get_category_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取分类数据表数据
        
        参数:
            limit: 限制返回的记录数，默认1000
            
        返回:
            分类数据列表
        """
        query = f"""
        SELECT *
        FROM skycrane_goods.t_base_category
        WHERE is_deleted = 0
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_category_count(self) -> int:
        """
        获取分类数据表总数
        
        返回:
            记录总数
        """
        query = """
        SELECT COUNT(1) as total
        FROM skycrane_goods.t_base_category
        WHERE is_deleted = 0
        """
        result = self.execute_query(query)
        return result[0]['total'] if result else 0
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        返回:
            连接是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logging.info("数据库连接测试成功")
                return True
        except Exception as e:
            logging.error(f"数据库连接测试失败: {e}")
            return False


# 创建全局数据源实例
b2b_mysql = B2BMySQLDataSource()


# 便捷函数
def get_b2b_mysql_source() -> B2BMySQLDataSource:
    """
    获取b2b MySQL数据源实例
    
    返回:
        B2BMySQLDataSource 实例
    """
    return b2b_mysql


if __name__ == "__main__":
    # 测试数据库连接和数据查询
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    db = B2BMySQLDataSource()
    
    # 测试连接
    print("=" * 60)
    print("开始测试数据库连接...")
    print("=" * 60)
    
    if db.test_connection():
        print("✓ 数据库连接成功！\n")
        
        # 测试查询节日数据
        print("=" * 60)
        print("测试查询节日数据表...")
        print("=" * 60)
        try:
            count = db.get_festival_count()
            print(f"节日数据表总数: {count}")
            
            festival_data = db.get_festival_data(limit=5)
            print(f"获取前5条节日数据:")
            for i, item in enumerate(festival_data, 1):
                print(f"  {i}. {item}")
        except Exception as e:
            print(f"查询节日数据失败: {e}")
        
        # 测试查询品牌数据
        print("\n" + "=" * 60)
        print("测试查询品牌数据表...")
        print("=" * 60)
        try:
            count = db.get_brand_count()
            print(f"品牌数据表总数: {count}")
            
            brand_data = db.get_brand_data(limit=5)
            print(f"获取前5条品牌数据:")
            for i, item in enumerate(brand_data, 1):
                print(f"  {i}. 品牌名称: {item.get('brand_name', 'N/A')}, 品牌编码: {item.get('brand_code', 'N/A')}")
        except Exception as e:
            print(f"查询品牌数据失败: {e}")
        
        # 测试查询分类数据
        print("\n" + "=" * 60)
        print("测试查询分类数据表...")
        print("=" * 60)
        try:
            count = db.get_category_count()
            print(f"分类数据表总数: {count}")
            
            category_data = db.get_category_data(limit=5)
            print(f"获取前5条分类数据:")
            for i, item in enumerate(category_data, 1):
                print(f"  {i}. 分类名称: {item.get('category_name', 'N/A')}, 分类编码: {item.get('category_code', 'N/A')}")
        except Exception as e:
            print(f"查询分类数据失败: {e}")
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
    else:
        print("✗ 数据库连接失败！")
