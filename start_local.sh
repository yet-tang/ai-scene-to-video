#!/bin/bash

# ============================================
# AI Scene to Video - 本地开发环境一键启动脚本
# ============================================
# 
# 功能：
# 1. 检查环境依赖（Docker, Docker Compose）
# 2. 自动准备 .env 文件（如果不存在）
# 3. 使用 docker-compose.dev.yml 启动所有服务（含 Postgres/Redis）
# 4. 提供访问地址和常用命令
#
# 使用方法：
#   chmod +x start_local.sh
#   ./start_local.sh
#
# 可选参数：
#   --rebuild : 强制重新构建镜像
#   --clean   : 清理所有容器和数据卷（慎用）
#   --logs    : 启动后显示实时日志
# ============================================

set -e  # 遇到错误立即退出

# ============ 颜色输出 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============ 检查依赖 ============
check_dependencies() {
    log_info "检查环境依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或版本过低（需要 Docker Compose V2）"
        exit 1
    fi
    
    # 检查 Docker Daemon 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行，请启动 Docker Desktop"
        exit 1
    fi
    
    log_success "环境依赖检查通过 ✓"
}

# ============ 准备 .env 文件 ============
prepare_env_file() {
    log_info "检查环境变量配置..."
    
    if [ ! -f .env ]; then
        log_warning ".env 文件不存在，正在从 .env.example 创建..."
        
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "已创建 .env 文件"
            log_warning "⚠️  请编辑 .env 文件，填写以下必需配置："
            echo ""
            echo "  必填项："
            echo "    - DASHSCOPE_API_KEY   (阿里云通义千问 API Key)"
            echo "    - S3_STORAGE_ENDPOINT (S3 存储端点)"
            echo "    - S3_STORAGE_ACCESS_KEY"
            echo "    - S3_STORAGE_SECRET_KEY"
            echo "    - S3_STORAGE_BUCKET"
            echo "    - S3_STORAGE_PUBLIC_URL"
            echo ""
            echo "  可选项（多智能体功能）："
            echo "    - VOLCENGINE_API_KEY  (火山引擎豆包 API Key)"
            echo "    - GROK_API_KEY        (X.AI Grok API Key)"
            echo ""
            read -p "是否现在编辑 .env 文件？(y/n) " -n 1 -r
            echo ""
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-vim} .env
            else
                log_warning "请稍后手动编辑 .env 文件后再次运行脚本"
                exit 0
            fi
        else
            log_error ".env.example 文件不存在，无法自动创建配置"
            exit 1
        fi
    else
        log_success ".env 文件已存在 ✓"
    fi
    
    # 验证关键配置
    source .env
    
    if [ -z "$DASHSCOPE_API_KEY" ]; then
        log_error "DASHSCOPE_API_KEY 未配置，请编辑 .env 文件"
        exit 1
    fi
    
    if [ -z "$S3_STORAGE_ENDPOINT" ]; then
        log_error "S3 存储未配置，请编辑 .env 文件"
        exit 1
    fi
    
    log_success "环境变量配置验证通过 ✓"
}

# ============ 清理环境 ============
clean_environment() {
    log_warning "正在清理所有容器和数据卷（包括数据库数据）..."
    read -p "⚠️  此操作不可恢复，是否继续？(y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "已取消清理操作"
        exit 0
    fi
    
    docker compose -f docker-compose.dev.yml down -v
    log_success "环境清理完成"
    exit 0
}

# ============ 启动服务 ============
start_services() {
    local rebuild_flag=""
    local logs_flag=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --rebuild)
                rebuild_flag="--build"
                shift
                ;;
            --logs)
                logs_flag=true
                shift
                ;;
            --clean)
                clean_environment
                ;;
            *)
                log_error "未知参数: $1"
                echo "用法: ./start_local.sh [--rebuild] [--logs] [--clean]"
                exit 1
                ;;
        esac
    done
    
    log_info "正在启动服务..."
    
    if [ -n "$rebuild_flag" ]; then
        log_info "强制重新构建镜像..."
    fi
    
    # 使用 docker-compose.dev.yml 启动
    docker compose -f docker-compose.dev.yml up -d $rebuild_flag
    
    log_success "服务启动成功！"
    echo ""
    echo "=========================================="
    echo "  AI Scene to Video - 本地开发环境"
    echo "=========================================="
    echo ""
    echo "服务访问地址："
    echo "  前端页面:     http://localhost"
    echo "  后端 API:     http://localhost:8090"
    echo "  健康检查:     http://localhost:8090/health"
    echo ""
    echo "Admin 管理后台："
    echo "  Admin 前端:   http://localhost:3001"
    echo "  Admin API:    http://localhost:8091"
    echo "  Flower:       http://localhost:5555 (admin/admin)"
    echo "  默认登录:     admin / admin123"
    echo ""
    echo "数据库连接信息："
    echo "  Host: localhost:5432"
    echo "  Database: ai_scene"
    echo "  Username: postgres"
    echo "  Password: postgres"
    echo ""
    echo "常用命令："
    echo "  查看日志:   docker compose -f docker-compose.dev.yml logs -f"
    echo "  停止服务:   docker compose -f docker-compose.dev.yml down"
    echo "  重启服务:   docker compose -f docker-compose.dev.yml restart"
    echo "  查看状态:   docker compose -f docker-compose.dev.yml ps"
    echo ""
    echo "=========================================="
    echo ""
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 5
    
    # 检查服务状态
    log_info "服务状态检查："
    docker compose -f docker-compose.dev.yml ps
    echo ""
    
    # 检查后端健康状态
    log_info "检查后端健康状态..."
    max_retries=30
    retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s http://localhost:8090/health > /dev/null; then
            log_success "后端服务已就绪 ✓"
            break
        fi
        
        retry_count=$((retry_count + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $retry_count -eq $max_retries ]; then
        log_warning "后端服务启动超时，请检查日志"
        log_info "查看后端日志: docker logs ai-scene-backend"
    fi
    
    echo ""
    
    # 如果指定了 --logs 参数，显示实时日志
    if [ "$logs_flag" = true ]; then
        log_info "显示实时日志（按 Ctrl+C 退出）..."
        docker compose -f docker-compose.dev.yml logs -f
    fi
}

# ============ 主函数 ============
main() {
    echo ""
    log_info "AI Scene to Video - 本地开发环境启动脚本"
    echo ""
    
    # 检查依赖
    check_dependencies
    
    # 准备环境变量
    prepare_env_file
    
    # 启动服务
    start_services "$@"
    
    log_success "启动流程完成！"
}

# 执行主函数
main "$@"
