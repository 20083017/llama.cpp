# -*- coding: utf-8 -*-
"""
用 Python 标准库（零依赖）手工构造真实的 GGUF 与 HF safetensors 二进制文件，
并做字节级解析，把解析结果注入到 HTML 对比文档中。
输出:
  - demo/ 目录下生成真实的 .gguf 与 .safetensors 文件
  - format_compare.html 自包含对比文档
"""
import struct, json, os, html

OUT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(OUT, "demo")
os.makedirs(DEMO, exist_ok=True)

# =====================================================================
# 1. GGUF 编码（按 gguf v3 规范手工写字节）
# =====================================================================
GGUF_TYPES = {
    "UINT32": 0, "INT32": 1, "FLOAT32": 2, "BOOL": 3,
    "STRING": 4, "ARRAY": 5, "UINT64": 10, "INT64": 11, "FLOAT64": 12,
}
# ggml dtype 枚举（节选）
GGML_DTYPES = {0: "F32", 1: "F16", 2: "Q4_0", 10: "Q8_0", 13: "Q4_K"}

def gguf_str(s):
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b

def gguf_kv(key, vtype, value_bytes):
    return gguf_str(key) + struct.pack("<I", vtype) + value_bytes

def encode_gguf():
    """构造一个最小但真实的 GGUF：1 个 UINT32 KV + 1 个 STRING KV + 2 个 F32 张量"""
    buf = bytearray()
    buf += struct.pack("<I", 0x46554747)          # 'GGUF' magic
    buf += struct.pack("<I", 3)                    # version
    buf += struct.pack("<Q", 2)                    # tensor_count
    buf += struct.pack("<Q", 2)                    # kv_count

    # KV1: general.architecture = "llama" (STRING)
    buf += gguf_kv("general.architecture", GGUF_TYPES["STRING"],
                   gguf_str("llama"))
    # KV2: llama.context_length = 4096 (UINT32)
    buf += gguf_kv("llama.context_length", GGUF_TYPES["UINT32"],
                   struct.pack("<I", 4096))

    # Tensor Info 表（2 个张量）
    tensors = [
        ("token_embd.weight", [4, 8], 0),     # 4x8 F32 = 128 bytes
        ("output.weight",     [4, 8], 0),
    ]
    for name, shape, dtype in tensors:
        buf += gguf_str(name)
        buf += struct.pack("<I", len(shape))          # n_dims
        for d in shape:
            buf += struct.pack("<Q", d)               # shape[]
        buf += struct.pack("<I", dtype)               # ggml dtype
        buf += struct.pack("<Q", 0)                   # offset 占位，后面回填

    # 数据块：按 32 字节对齐
    pad = (-len(buf)) % 32
    buf += b"\x00" * pad
    off1 = len(buf)
    data1 = struct.pack("<32f", *[float(i) / 100 for i in range(32)])  # 4x8 F32
    buf += data1
    off2 = len(buf)
    buf += data1  # 第二个张量同样 128 字节

    # 回填两个 offset（位于 tensor info 表内固定位置，手动计算）
    # 简化：直接重新构造带正确 offset 的 info 区
    # 这里用二次构建保证正确
    return _rebuild_gguf(off1, off2)

def _rebuild_gguf(off1, off2):
    buf = bytearray()
    buf += struct.pack("<I", 0x46554747)
    buf += struct.pack("<I", 3)
    buf += struct.pack("<Q", 2)
    buf += struct.pack("<Q", 2)
    buf += gguf_kv("general.architecture", GGUF_TYPES["STRING"], gguf_str("llama"))
    buf += gguf_kv("llama.context_length", GGUF_TYPES["UINT32"], struct.pack("<I", 4096))
    tensors = [("token_embd.weight", [4, 8], 0, off1), ("output.weight", [4, 8], 0, off2)]
    for name, shape, dtype, off in tensors:
        buf += gguf_str(name)
        buf += struct.pack("<I", len(shape))
        for d in shape:
            buf += struct.pack("<Q", d)
        buf += struct.pack("<I", dtype)
        buf += struct.pack("<Q", off)
    pad = (-len(buf)) % 32
    buf += b"\x00" * pad
    data1 = struct.pack("<32f", *[float(i) / 100 for i in range(32)])
    buf += data1
    buf += data1
    return bytes(buf)

def parse_gguf(data):
    """字节级解析 GGUF，返回结构化结果"""
    r = {}
    r["magic"] = data[:4]
    r["version"] = struct.unpack("<I", data[4:8])[0]
    r["tensor_count"] = struct.unpack("<Q", data[8:16])[0]
    r["kv_count"] = struct.unpack("<Q", data[16:24])[0]
    pos = 24
    kvs = []
    for _ in range(r["kv_count"]):
        klen = struct.unpack("<Q", data[pos:pos+8])[0]; pos += 8
        key = data[pos:pos+klen].decode(); pos += klen
        vtype = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
        if vtype == GGUF_TYPES["UINT32"]:
            val = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
        elif vtype == GGUF_TYPES["STRING"]:
            slen = struct.unpack("<Q", data[pos:pos+8])[0]; pos += 8
            val = data[pos:pos+slen].decode(); pos += slen
        else:
            val = f"<type {vtype}>"
        kvs.append((key, vtype, val))
    r["kvs"] = kvs
    tensors = []
    for _ in range(r["tensor_count"]):
        nlen = struct.unpack("<Q", data[pos:pos+8])[0]; pos += 8
        name = data[pos:pos+nlen].decode(); pos += nlen
        ndims = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
        shape = [struct.unpack("<Q", data[pos+8*i:pos+8*i+8])[0] for i in range(ndims)]
        pos += 8*ndims
        dtype = struct.unpack("<I", data[pos:pos+4])[0]; pos += 4
        offset = struct.unpack("<Q", data[pos:pos+8])[0]; pos += 8
        tensors.append({"name": name, "shape": shape, "dtype": dtype,
                        "dtype_name": GGML_DTYPES.get(dtype, str(dtype)), "offset": offset})
    r["tensors"] = tensors
    r["header_end"] = pos
    r["data_start_aligned"] = tensors[0]["offset"] if tensors else pos
    r["total_size"] = len(data)
    return r

# =====================================================================
# 2. safetensors 编码（手工写字节）
# =====================================================================
def encode_safetensors():
    """构造一个最小 safetensors：2 个 F32 张量，header 为 JSON"""
    t0 = struct.pack("<32f", *[float(i) for i in range(32)])  # 4x8 F32 = 128B
    t1 = struct.pack("<8f", *[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])  # 2x4 = 32B
    header = {
        "a.weight": {"dtype": "F32", "shape": [4, 8], "data_offsets": [0, len(t0)]},
        "b.weight": {"dtype": "F32", "shape": [2, 4], "data_offsets": [len(t0), len(t0)+len(t1)]},
        "__metadata__": {"format": "pt"},
    }
    hjson = json.dumps(header, separators=(",", ":")).encode("utf-8")
    return struct.pack("<Q", len(hjson)) + hjson + t0 + t1

def parse_safetensors(data):
    """字节级解析 safetensors"""
    r = {}
    hlen = struct.unpack("<Q", data[:8])[0]
    r["header_len"] = hlen
    r["header_json"] = data[8:8+hlen].decode("utf-8")
    r["header"] = json.loads(r["header_json"])
    r["data_start"] = 8 + hlen
    r["total_size"] = len(data)
    return r

# =====================================================================
# 3. 生成解析结果 + HTML
# =====================================================================
gguf_bytes = encode_gguf()
st_bytes = encode_safetensors()
with open(os.path.join(DEMO, "demo.gguf"), "wb") as f:
    f.write(gguf_bytes)
with open(os.path.join(DEMO, "demo.safetensors"), "wb") as f:
    f.write(st_bytes)

gguf_r = parse_gguf(gguf_bytes)
st_r = parse_safetensors(st_bytes)

# 十六进制 dump（前 96 字节）
def hexdump(data, n=96):
    lines = []
    for i in range(0, min(n, len(data)), 16):
        chunk = data[i:i+16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:06x}  {hexs:<47}  {ascii_}")
    return "\n".join(lines)

gguf_hex = hexdump(gguf_bytes)
st_hex = hexdump(st_bytes)

# 构造 HTML
def esc(s):
    return html.escape(str(s))

kvs_html = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td>{esc(t)}</td><td><code>{esc(v)}</code></td></tr>"
    for k, t, v in gguf_r["kvs"]
)
tens_gguf_html = "".join(
    f"<tr><td><code>{esc(t['name'])}</code></td><td>{esc(t['shape'])}</td>"
    f"<td><code>{esc(t['dtype_name'])}</code></td><td>{esc(t['offset'])}</td></tr>"
    for t in gguf_r["tensors"]
)
tens_st_html = "".join(
    f"<tr><td><code>{esc(k)}</code></td><td><code>{esc(v['dtype'])}</code></td>"
    f"<td>{esc(v['shape'])}</td><td>{esc(v['data_offsets'])}</td></tr>"
    for k, v in st_r["header"].items() if not k.startswith("__")
)

html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HF safetensors vs GGUF 格式解析对比</title>
<style>
:root {{
  --bg: #16181d; --surface: #1e2128; --surface2: #262a33;
  --border: #333843; --text: #e6e8ec; --muted: #9aa0ad;
  --accent: #5dc9a5; --accent2: #a7a4f0; --amber: #ef9f27;
  --mono: "Consolas","Cascadia Code","JetBrains Mono",monospace;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height: 1.7; font-size: 15px;
}}
.wrap {{ max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }}
h1 {{ font-size: 28px; font-weight: 600; margin: 0 0 8px; }}
h2 {{ font-size: 21px; font-weight: 600; margin: 44px 0 12px; padding-top: 20px; border-top: 1px solid var(--border); }}
h3 {{ font-size: 17px; font-weight: 600; margin: 28px 0 8px; }}
p {{ margin: 10px 0; color: var(--text); }}
.sub {{ color: var(--muted); font-size: 14px; }}
code {{
  font-family: var(--mono); font-size: 13px; background: var(--surface2);
  padding: 2px 6px; border-radius: 4px; color: #d9e2ec;
}}
pre {{
  background: #0f1115; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px 16px; overflow-x: auto; font-family: var(--mono);
  font-size: 12.5px; line-height: 1.55; color: #c8d3de;
}}
table {{ border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 14px; }}
th, td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: left; }}
th {{ background: var(--surface2); font-weight: 600; }}
tr:nth-child(even) td {{ background: var(--surface); }}
.callout {{
  border-left: 3px solid var(--accent); background: var(--surface);
  padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0;
}}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
.tag.hf {{ background: #2c2340; color: #b6aee0; }}
.tag.gguf {{ background: #0c3a30; color: #7fd6b5; }}
.badge {{ color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<div class="wrap">
<h1>HF safetensors vs GGUF 格式解析对比</h1>
<p class="sub">字节级编码与数据结构设计详解 · 含真实二进制解析示例（Python 标准库零依赖构造）</p>

<div class="callout">
<strong>一句话结论：</strong>两者都是「元数据头 + 连续张量字节流」的二进制格式，但 <span class="tag hf">safetensors</span> 面向<strong>训练/框架耦合</strong>（JSON 头按张量名索引、dtype 保真、多文件分片），而 <span class="tag gguf">GGUF</span> 面向<strong>消费级单文件推理</strong>（全二进制 KV 头、内嵌架构与 tokenizer、原生量化、mmap 延迟加载）。
</div>

<h2>1. 核心设计哲学</h2>
<table>
<tr><th>维度</th><th>HF safetensors</th><th>GGUF</th></tr>
<tr><td>设计目标</td><td>训练 + PyTorch/transformers 推理</td><td>消费级 CPU/GPU 单文件推理</td></tr>
<tr><td>文件数量</td><td>多文件（shard + config.json + tokenizer）</td><td>单文件自包含</td></tr>
<tr><td>架构信息</td><td>无，靠外部 config.json</td><td>内嵌 <code>general.architecture</code> KV</td></tr>
<tr><td>张量寻址</td><td>JSON header 按名 → offset</td><td>KV + Tensor Info 表 → offset</td></tr>
<tr><td>dtype</td><td>原始 dtype 保真（F32/F16/BF16）</td><td>ggml 枚举 + 量化类型（Q4_K 等）</td></tr>
<tr><td>内存策略</td><td>mmap（可选）、完整加载</td><td>mmap + 延迟换页（核心）</td></tr>
<tr><td>量化</td><td>通常不量化</td><td>原生量化，直接存量化权重</td></tr>
<tr><td>依赖</td><td>需 PyTorch 生态</td><td>零依赖，任意语言可解析</td></tr>
<tr><td>元数据</td><td>JSON 文本 + <code>__metadata__</code></td><td>全二进制 KV（type tag），极灵活</td></tr>
</table>

<h2>2. 文件布局（编码结构）</h2>
<h3>2.1 safetensors 布局</h3>
<pre>[8 字节小端 u64: header 长度 N]
[N 字节 UTF-8 JSON header]
[连续张量字节流：tensor0, tensor1, ...]</pre>
<p>header 是 JSON 文本，逐张量记录 dtype / shape / data_offsets。加载器解析 JSON 后按 offset 随机访问。</p>

<h3>2.2 GGUF 布局</h3>
<pre>[Magic 'GGUF' + version + tensor_count + kv_count]
[KV 元数据块：key + value类型标记 + value字节 × N]
[Tensor Info 表：name + n_dims + shape[] + ggml_dtype + offset × M]
[Tensor 数据块：按 32 字节对齐的连续字节流]</pre>
<p>KV 的 value 类型由一个 type tag 枚举标记，支持整数/浮点/布尔/字符串/数组，因此架构、超参数、词表、chat 模板都能塞进同一个文件。</p>

<h2>3. 真实二进制解析示例</h2>
<p class="sub">以下字节由脚本用 <code>struct</code> 按规范手工构造（非伪造概念图），并真实解析回来。文件已落盘于 <code>demo/demo.gguf</code> 与 <code>demo/demo.safetensors</code>。</p>

<h3>3.1 GGUF 解析结果（总 {gguf_r['total_size']} 字节）</h3>
<pre>magic         = {esc(gguf_r['magic'])}   (0x46554747)
version       = {gguf_r['version']}
tensor_count  = {gguf_r['tensor_count']}
kv_count      = {gguf_r['kv_count']}
header_end    = byte {gguf_r['header_end']}
data_start    = byte {gguf_r['data_start_aligned']}   (32 字节对齐)</pre>
<h4>KV 元数据</h4>
<table>
<tr><th>key</th><th>type tag</th><th>value</th></tr>
{kvs_html}
</table>
<h4>Tensor Info 表</h4>
<table>
<tr><th>name</th><th>shape</th><th>dtype</th><th>offset</th></tr>
{tens_gguf_html}
</table>
<h4>头部字节（十六进制）</h4>
<pre>{esc(gguf_hex)}</pre>

<h3>3.2 safetensors 解析结果（总 {st_r['total_size']} 字节）</h3>
<pre>header_len  = {st_r['header_len']} 字节
data_start  = byte {st_r['data_start']}</pre>
<h4>Header JSON</h4>
<pre>{esc(st_r['header_json'])}</pre>
<h4>张量</h4>
<table>
<tr><th>name</th><th>dtype</th><th>shape</th><th>data_offsets</th></tr>
{tens_st_html}
</table>
<h4>头部字节（十六进制）</h4>
<pre>{esc(st_hex)}</pre>

<h2>4. 关键设计差异：为什么会有两个平行宇宙</h2>
<table>
<tr><th>关注点</th><th>safetensors 的选择</th><th>GGUF 的选择</th></tr>
<tr><td>谁在读</td><td>PyTorch <code>state_dict</code></td><td>任意推理引擎（C/Rust/Go/Py）</td></tr>
<tr><td>数值</td><td>必须精确（训练）→ 不量化</td><td>可容忍有损（推理）→ 大量量化</td></tr>
<tr><td>部署</td><td>一个目录多文件</td><td>一个文件拷走即用</td></tr>
<tr><td>元数据扩展</td><td>JSON 键值，扩展需改解析约定</td><td>KV type-tag，天然可增字段</td></tr>
</table>

<h2>5. 转换桥梁</h2>
<p><code>llama.cpp/convert_hf_to_gguf.py</code> 读 HF 的 <code>config.json</code> + <code>tokenizer.json</code> + safetensors 权重，把架构字段、超参数、词表、chat 模板写成 GGUF 的 KV，把权重按新命名（<code>blk.0.attn_q.weight</code>）量化后写入 GGUF。</p>

<p class="sub">生成时间：2026-11-03 · 解析脚本 <code>build_format_doc.py</code> · 样例文件 <code>demo/</code></p>
</div>
</body>
</html>
"""

with open(os.path.join(OUT, "format_compare.html"), "w", encoding="utf-8") as f:
    f.write(html_doc)

print("GGUF  total bytes:", len(gguf_bytes))
print("safetensors total bytes:", len(st_bytes))
print("HTML written:", os.path.join(OUT, "format_compare.html"))
print("demo files:", os.listdir(DEMO))
