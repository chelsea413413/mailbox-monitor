# 厅长信箱自动监测系统

自动监测各省生态环境厅厅长信箱，每日定时采集新增回复与内容更新，生成 HTML 邮件日报和 Excel 明细附件。

## 系统架构

```
provinces.yaml (23省配置)
        |
        v
   main.py (主编排器)
    /    |    \
   /     |     \
crawl   diff   report
(采集)  (比对)  (报告)
  |       |       |
  v       v       v
Adapter  DB     Email+Excel
(每省独立) (SQLite)  (SMTP)
```

### 核心设计原则

- **每省一个独立 Crawler**：`src/crawlers/` 下每个省份一个 `.py` 文件，网站改版时只需修改对应文件
- **HTTP 优先，Playwright 兜底**：静态/API 站点用 httpx，动态渲染站点用 Playwright
- **Hash 比对而非日期判断**：通过 `original_id + content_hash` 识别真正的新增和内容更新
- **"今日无新增" vs "采集失败"**：日报中明确区分两种状态，避免误判

### 统一字段

| 字段 | 说明 |
|------|------|
| province | 省份 |
| title | 信件标题 |
| publish_date | 发布日期 |
| reply_date | 回复日期 |
| content | 咨询内容 |
| reply_content | 回复内容 |
| url | 原文 URL |
| original_id | 网站原始 ID |

## 目录结构

```
mailbox-monitor/
  config/
    settings.yaml        全局配置（数据库、采集、邮件、日志）
    provinces.yaml       各省网址与适配器映射
    .env.example         环境变量模板
  src/
    main.py              主编排器
    base_crawler.py      采集器基类（HTTP/Playwright/retry/结构检测）
    models.py            统一数据模型
    database.py          SQLite 数据库层
    diff_engine.py       Hash 差异引擎
    email_reporter.py    HTML 报告渲染 + SMTP 发送
    excel_generator.py   Excel 明细生成
    logger.py            日志配置
    retry.py             重试装饰器
    crawlers/
      generic_http.py    通用 HTTP 采集器（可配置选择器）
      registry.py        采集器注册表
      sichuan.py         四川省适配器
      hunan.py           湖南省适配器
      ...                每省一个文件
  templates/
    daily_report.html.j2 HTML 邮件模板
  Dockerfile             Docker 镜像
  docker-compose.yml     本地 Docker 运行
  .github/workflows/
    daily-crawl.yml      GitHub Actions 定时任务
  requirements.txt       Python 依赖
```

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 配置环境变量
cp config/.env.example config/.env
# 编辑 .env 填入 SMTP 信息

# 运行全部省份（试运行，不发送邮件）
python -m src.main --dry-run

# 运行指定省份
python -m src.main sichuan hunan

# 运行全部并发送邮件
python -m src.main
```

## Docker 部署

```bash
# 构建镜像
docker build -t mailbox-monitor .

# 运行
docker compose run --rm mailbox-monitor

# 或直接 docker run
docker run --rm \
  --env-file config/.env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  mailbox-monitor
```

## GitHub Actions 云端部署

1. 将代码推送到 GitHub 仓库
2. 在仓库 Settings > Secrets and variables > Actions 中添加：
   - `SMTP_HOST` - SMTP 服务器地址
   - `SMTP_PORT` - SMTP 端口（SSL 通常为 465）
   - `SMTP_USER` - 发件邮箱
   - `SMTP_PASSWORD` - 邮箱密码/授权码
   - `MAIL_TO` - 收件人（多个用逗号分隔）
3. 工作流每天 19:00 和 22:00（北京时间）自动运行
4. 也可在 Actions 页面手动触发（workflow_dispatch）

### 数据库持久化

SQLite 数据库通过 GitHub Actions Cache 在每次运行间持久化：
- 每次运行前从缓存恢复 `data/` 目录
- 运行后将更新后的数据库存入新缓存
- 日志和输出文件作为 Artifact 保留 30 天

## 添加/修改省份适配器

### 修改现有适配器

当某省网站改版时，只需修改 `src/crawlers/{province}.py` 中的选择器配置：

```python
class SichuanCrawler(GenericHttpCrawler):
    # 修改这些选择器以匹配新网站结构
    list_container = ".news-list li"
    detail_content_sel = ".article-content"
    detail_reply_sel = ".reply-box"
```

### 添加新省份

1. 在 `src/crawlers/` 下创建新文件（如 `xprovince.py`）
2. 继承 `GenericHttpCrawler`（HTTP 站点）或 `BaseCrawler`（API/Playwright 站点）
3. 在 `src/crawlers/registry.py` 中注册
4. 在 `config/provinces.yaml` 中添加配置

### 采集器类型

| 类型 | 适用场景 | 基类 |
|------|---------|------|
| http | 静态 HTML 页面 | GenericHttpCrawler |
| api | JSON API 接口 | BaseCrawler（自定义） |
| playwright | JS 动态渲染 | BaseCrawler + playwright_fetch() |

## 数据库表结构

### letters（信件主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| province | TEXT | 省份 |
| original_id | TEXT | 网站原始 ID |
| title | TEXT | 标题 |
| url | TEXT | 原文 URL |
| publish_date | TEXT | 发布日期 |
| reply_date | TEXT | 回复日期 |
| content | TEXT | 咨询内容 |
| reply_content | TEXT | 回复内容 |
| content_hash | TEXT | 内容 SHA-256 |
| first_seen | TEXT | 首次发现时间 |
| last_updated | TEXT | 最近更新时间 |
| last_checked | TEXT | 最近检查时间 |

### crawl_logs（采集日志）

记录每次采集运行的省份、状态、条目数、耗时等。

### structure_alerts（结构告警）

记录网站结构变化告警，用于跟踪网站改版情况。

## 后续扩展方向

- [ ] Web 管理后台（Flask/FastAPI）
- [ ] 历史查询与统计面板
- [ ] 关键词监控告警
- [ ] AI 摘要生成
- [ ] 微信小程序查看
- [ ] 云数据库替代 SQLite（PostgreSQL/Supabase）
