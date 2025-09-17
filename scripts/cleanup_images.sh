#!/bin/bash
# 图片清理脚本 - 简化版本
# 使用方法: ./cleanup_images.sh [选项]

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示帮助信息
show_help() {
    echo "图片清理工具 - 简化版本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  stats          显示图片统计信息"
    echo "  cleanup-unreferenced 清理未被日记引用的图片文件（推荐）"
    echo "  dry-run        模拟运行（不实际删除）"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 stats                           # 显示统计信息"
    echo "  $0 cleanup-unreferenced            # 清理未被日记引用的图片文件"
    echo "  $0 cleanup-unreferenced --dry-run  # 模拟清理（不实际删除）"
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装或不在PATH中"
        exit 1
    fi
}

# 检查脚本文件
check_scripts() {
    if [ ! -f "cleanup_unreferenced_images.py" ]; then
        print_error "清理脚本文件不存在: cleanup_unreferenced_images.py"
        exit 1
    fi
}

# 显示统计信息
show_stats() {
    print_info "显示图片统计信息..."
    python3 cleanup_unreferenced_images.py --dry-run
}

# 清理未被日记引用的图片文件
cleanup_unreferenced() {
    print_info "清理未被日记引用的图片文件..."
    python3 cleanup_unreferenced_images.py
}

# 模拟运行
dry_run() {
    print_warning "模拟模式 - 不会实际删除文件"
    python3 cleanup_unreferenced_images.py --dry-run
}

# 主函数
main() {
    # 检查环境
    check_python
    check_scripts
    
    # 解析参数
    case "${1:-help}" in
        "stats")
            show_stats
            ;;
        "cleanup-unreferenced")
            cleanup_unreferenced
            ;;
        "dry-run")
            dry_run
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
