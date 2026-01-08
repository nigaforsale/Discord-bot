import socket
import dns.resolver

def resolve_dns(input_str):
    print(f"\n🔍 正在解析: {input_str}")
    print("-" * 40)
    
    # 判斷是否為 IP 位址
    try:
        socket.inet_aton(input_str)
        # 執行反向解析 (PTR)
        try:
            result = socket.gethostbyaddr(input_str)
            print(f"📌 [反向解析結果] 主機名稱: {result[0]}")
        except socket.herror:
            print("❌ 找不到該 IP 對應的主機名稱。")
        return # IP 不需要查 CNAME，直接結束
    except socket.error:
        pass

    # 執行正向解析 (Domain)
    resolver = dns.resolver.Resolver()
    
    # 1. 查詢 CNAME (別名)
    try:
        cname_answers = resolver.resolve(input_str, 'CNAME')
        print(f"📌 [別名紀錄 - CNAME Record]")
        for rdata in cname_answers:
            print(f"目標指向 (Target): {rdata.target}")
    except dns.resolver.NoAnswer:
        print("ℹ️ 該網域沒有 CNAME 紀錄 (可能直接指向 A 紀錄)。")
    except dns.resolver.NXDOMAIN:
        print(f"❌ 錯誤: 網域 {input_str} 不存在。")
        return
    except Exception as e:
        print(f"⚠️ 查詢 CNAME 時發生異常: {e}")

    # 2. 查詢 A 紀錄 (IPv4)
    try:
        print(f"\n📌 [正向解析 - A Record]")
        a_answers = resolver.resolve(input_str, 'A')
        for rdata in a_answers:
            print(f"IPv4 地址: {rdata.address}")
    except Exception:
        print("無 A 紀錄。")

if __name__ == "__main__":
    target = input("請輸入 Domain (例如 www.github.com): ").strip()
    resolve_dns(target)