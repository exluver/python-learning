from pathlib import Path
import re

# ====== SETTINGS ======
root_folder = Path(r"Enter your path here...")
# ======================

# ====== Счетчики ======
gdn_count = 0
rtb_count = 0
already_patched_count = 0
skipped_count = 0

# ====== Цвета для терминала ======
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    RESET = '\033[0m'

# ====== Вспомогательные функции ======
def parse_banner_size(filename: str):
    """Находит два числа в имени файла, как ширину и высоту"""
    numbers = re.findall(r'\d+', filename)
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    return None, None

def is_already_patched(html_path: Path, banner_type: str, banner_width: str, banner_height: str):
    """Проверяем, пропатчен ли файл"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            meta_check = f'width={banner_width},height={banner_height}' in content
            if banner_type == "GDN":
                link_check = 'window.clickTag' in content
            else:
                link_check = 'yandexHTML5BannerApi.getClickURLNum' in content
            return meta_check and link_check
    except (OSError, IOError):
        return False

def patch_gdn_line(line: str, counter_data: dict, width: str, height: str):
    line_norm = line.strip()
    if line_norm == '<meta name="authoring-tool" content="Adobe_Animate_CC">':
        return f'<meta name="ad.size" content="width={width},height={height}">\n'
    elif line_norm == '<script src="https://code.createjs.com/1.0.0/createjs.min.js"></script>' \
            and counter_data['counter_2'] == 0:
        counter_data['counter_2'] += 1
        return '<script src="https://s0.2mdn.net/ads/studio/cached_libs/createjs_2019.11.15_min.js"></script>\n'
    elif line_norm == '<!-- write your code here -->':
        counter_data['counter'] += 1
        if counter_data['counter'] > 1:
            return '<script type="text/javascript"> var clickTag = "http://www.google.com"; </script>\n'
    elif line_norm == '<body onload="init();" style="margin:0px;">':
        return '<body onload="init();" style="margin:0px;">\n    <a href="javascript:window.open(window.clickTag)">\n'
    elif line_norm == '</body>':
        return '    </a>\n</body>\n'
    return line

def patch_rtb_line(line: str, width: str, height: str):
    line_norm = line.strip()
    if line_norm == '<meta name="authoring-tool" content="Adobe_Animate_CC">':
        return (
            '<meta name="authoring-tool" content="Adobe_Animate_CC">\n'
            f'<meta name="ad.size" content="width={width},height={height}">\n'
        )
    elif line_norm == '<body onload="init();" style="margin:0px;">':
        return '<body onload="init();" style="margin:0px;">\n    <a id="click_area" href="#" target="_blank">\n'
    elif line_norm == '</body>':
        return (
            '    </a>\n'
            '    <script>document.getElementById("click_area").href = yandexHTML5BannerApi.getClickURLNum(1);</script>\n'
            '</body>\n'
        )
    return line

# ====== Основной процессинг файла ======
def process_html_file(html_path: Path):
    global gdn_count, rtb_count, already_patched_count, skipped_count

    html_file_name = html_path.name

    banner_width, banner_height = parse_banner_size(html_file_name)
    if not banner_width or not banner_height:
        print(f"{Colors.RED}[SKIP]{Colors.RESET} Cannot parse size from filename: {html_file_name}")
        skipped_count += 1
        return

    images_folder = html_path.parent / "images"
    if not images_folder.is_dir():
        print(f"{Colors.RED}[SKIP]{Colors.RESET} {html_file_name} has no 'images' folder.")
        skipped_count += 1
        return

    image_files = [p for p in images_folder.iterdir() if p.is_file()]
    if not image_files:
        print(f"{Colors.RED}[SKIP]{Colors.RESET} {html_file_name} has empty 'images' folder.")
        skipped_count += 1
        return

    banner_type = "RTB" if len(image_files) == 1 else "GDN"

    if is_already_patched(html_path, banner_type, banner_width, banner_height):
        print(f"{Colors.CYAN}[ALREADY PROCESSED]{Colors.RESET} {html_file_name}")
        already_patched_count += 1
        return

    counter_data = {'counter':0, 'counter_2':0}
    with open(html_path, 'r', encoding='utf-8') as f:
        new_file = ''
        for line in f:
            if banner_type == "GDN":
                new_file += patch_gdn_line(line, counter_data, banner_width, banner_height)
            else:
                new_file += patch_rtb_line(line, banner_width, banner_height)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_file)

    if banner_type == "GDN":
        gdn_count += 1
        print(f"{Colors.GREEN}[OK]{Colors.RESET} {html_file_name} converted as {banner_type}")
    else:
        rtb_count += 1
        print(f"{Colors.BLUE}[OK]{Colors.RESET} {html_file_name} converted as {banner_type}")

# ====== Рекурсивный обход папок ======
def recursive_process(folder: Path):
    if not folder.exists():
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Folder not found: {folder}")
        return
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() == '.html':
            process_html_file(item)
        elif item.is_dir():
            recursive_process(item)

# ====== Запуск ======
recursive_process(root_folder)

# ====== Финальный лог ======
print("\n=== SUMMARY ===")
print(f"{Colors.GREEN}GDN banners converted: {gdn_count}{Colors.RESET}")
print(f"{Colors.BLUE}RTB banners converted: {rtb_count}{Colors.RESET}")
print(f"{Colors.CYAN}Already processed files: {already_patched_count}{Colors.RESET}")
print(f"{Colors.RED}Skipped files (invalid/empty): {skipped_count}{Colors.RESET}")
