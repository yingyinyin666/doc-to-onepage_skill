#!/usr/bin/env python3
"""
OnePage V2 截图校验脚本
使用 Playwright 进行视觉质量检查，适配 V2 模板结构。
"""
import argparse
import os


def check_playwright_installed():
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def take_screenshot(html_path, output_path=None):
    from playwright.sync_api import sync_playwright

    if not os.path.exists(html_path):
        print(f"Error: HTML file not found: {html_path}")
        return None

    if output_path is None:
        output_path = html_path.replace('.html', '_screenshot.png')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.goto(f'file://{os.path.abspath(html_path)}')
        page.wait_for_timeout(1500)  # V2 有动画，等稍久
        page.screenshot(path=output_path, full_page=True)
        browser.close()

    return output_path


def analyze_visual_quality(html_path):
    from playwright.sync_api import sync_playwright

    issues = []
    checks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.goto(f'file://{os.path.abspath(html_path)}')
        page.wait_for_timeout(1500)

        # V2 结论区域
        has_conclusion = page.query_selector('.conclusion')
        checks.append({
            'item': '结论区域',
            'passed': has_conclusion is not None,
        })

        # V2 CTA 决策框
        has_cta = page.query_selector('.conclusion-cta')
        # fallback: 检查结论区内是否有加粗的决策问句
        if not has_cta:
            has_cta = page.query_selector('.conclusion-content strong')
        checks.append({
            'item': 'CTA决策框',
            'passed': has_cta is not None,
        })

        # 标题层级
        h1_count = len(page.query_selector_all('h1'))
        h2_count = len(page.query_selector_all('.card-head h2'))
        checks.append({
            'item': '标题层级',
            'passed': h1_count >= 1 and h2_count <= 8,
            'h1': h1_count,
            'h2': h2_count
        })

        # V2 卡片模块数量
        cards = page.query_selector_all('.card')
        checks.append({
            'item': '模块数量',
            'passed': len(cards) <= 8,
            'count': len(cards)
        })

        # V2 可视化组件
        metric_cards = page.query_selector_all('.metric-card')
        flow_steps = page.query_selector_all('.flow-step')
        journey_stages = page.query_selector_all('.journey-stage')
        priority_badges = page.query_selector_all('.priority-badge')
        risk_levels = page.query_selector_all('.risk-level')
        viz_count = (len(metric_cards) + len(flow_steps) + len(journey_stages)
                     + len(priority_badges) + len(risk_levels))
        checks.append({
            'item': '可视化组件',
            'passed': viz_count >= 1,
            'count': viz_count,
            'detail': {
                'metric_cards': len(metric_cards),
                'flow_steps': len(flow_steps),
                'journey_stages': len(journey_stages),
                'priority_badges': len(priority_badges),
                'risk_levels': len(risk_levels),
            }
        })

        # 风险模块
        has_risk = page.query_selector('.sec-risk')
        checks.append({
            'item': '风险模块',
            'passed': has_risk is not None,
        })

        # 内容可见性
        visible_text = page.evaluate('''() => {
            const el = document.body;
            const style = window.getComputedStyle(el);
            return {
                visible: style.visibility !== 'hidden' && style.display !== 'none',
                hasContent: el.innerText.length > 100
            };
        }''')
        checks.append({
            'item': '内容可见性',
            'passed': visible_text['visible'] and visible_text['hasContent'],
        })

        browser.close()

    for check in checks:
        if not check['passed']:
            detail = ''
            if 'count' in check:
                detail = f" ({check['count']}个)"
            if 'h1' in check:
                detail = f" (H1:{check['h1']}, H2:{check['h2']})"
            issues.append(f"{check['item']}: 未通过{detail}")

    return {
        'checks': checks,
        'issues': issues,
        'score': max(0, 100 - len(issues) * 12)
    }


def main():
    parser = argparse.ArgumentParser(description="OnePage V2 截图校验")
    parser.add_argument('--html', type=str, required=True, help='HTML文件路径')
    parser.add_argument('--screenshot', type=str, help='截图保存路径')
    parser.add_argument('--analyze', action='store_true', help='进行视觉分析')

    args = parser.parse_args()

    if not check_playwright_installed():
        print("Playwright 未安装")
        print("请运行: pip install playwright && playwright install chromium")
        return

    print("=" * 50)
    print("OnePage V2 截图校验")
    print("=" * 50)

    screenshot_path = take_screenshot(args.html, args.screenshot)
    if screenshot_path:
        print(f"\n截图已保存: {screenshot_path}")

    if args.analyze:
        print("\n视觉质量分析...")
        analysis = analyze_visual_quality(args.html)

        print(f"\n视觉得分: {analysis['score']}/100")
        print("\n检查结果:")
        for check in analysis['checks']:
            status = 'PASS' if check['passed'] else 'FAIL'
            extra = ''
            if 'count' in check:
                extra = f" ({check['count']}个)"
            if 'h1' in check:
                extra = f" (H1:{check['h1']}, H2:{check['h2']})"
            if 'detail' in check and isinstance(check['detail'], dict):
                parts = [f"{k}:{v}" for k, v in check['detail'].items() if v > 0]
                if parts:
                    extra = f" ({', '.join(parts)})"
            print(f"  [{status}] {check['item']}{extra}")

        if analysis['issues']:
            print(f"\n发现问题 ({len(analysis['issues'])}项):")
            for issue in analysis['issues']:
                print(f"  - {issue}")
        else:
            print("\n视觉质量检查全部通过")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
