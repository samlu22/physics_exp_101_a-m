import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import numpy as np
import os
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 物理計算函數
def calculate_acceleration(m, M, theta, f, g=9.8):
    """
    計算滑車-砝碼系統的加速度
    
    Parameters:
    m: 砝碼質量 (kg)
    M: 滑車質量 (kg) 
    theta: 斜面角度 (度)
    f: 摩擦力 (N)
    g: 重力加速度 (m/s²)
    
    Returns:
    acceleration: 加速度 (m/s²)，正值表示向上運動
    """
    theta_rad = np.radians(theta)
    mg_sin = M * g * np.sin(theta_rad)
    
    # 向上運動條件：mg > Mg*sin(θ) + f
    if m * g > mg_sin + f:
        return (m * g - mg_sin - f) / (M + m)
    # 向下運動條件：mg < Mg*sin(θ) - f  
    elif m * g < mg_sin - f:
        return -(mg_sin - f - m * g) / (M + m)
    else:
        # 平衡區域（靜摩擦範圍內）
        return 0

def calculate_critical_masses(M, theta, f, g=9.8):
    """
    計算臨界質量 m+ 和 m-
    
    Parameters:
    M: 滑車質量 (kg) - 注意：必須是公斤
    theta: 斜面角度 (度)
    f: 摩擦力 (N)
    g: 重力加速度 (m/s²)
    
    Returns:
    m_plus, m_minus: 臨界質量 (kg)
    """
    theta_rad = np.radians(theta)
    mg_sin = M * g * np.sin(theta_rad)
    
    m_plus = (mg_sin + f) / g  # 開始向上運動的臨界質量
    m_minus = max(0, (mg_sin - f) / g)  # 開始向下運動的臨界質量
    
    return m_plus, m_minus

def generate_data_points(M, theta, f, m_min=10, m_max=300, num_points=50):
    """
    生成 a-m 數據點
    
    Parameters:
    M: 滑車質量 (g)
    theta: 斜面角度 (度)
    f: 摩擦力 (N)
    m_min, m_max: 砝碼質量範圍 (g)
    num_points: 數據點數量
    
    Returns:
    data: 數據點列表
    """
    m_range = np.linspace(m_min, m_max, num_points)
    
    data = []
    for m_g in m_range:
        m_kg = m_g / 1000  # 轉換為kg
        M_kg = M / 1000    # 轉換為kg
        a = calculate_acceleration(m_kg, M_kg, theta, f)
        data.append({
            'mass_g': m_g,
            'mass_kg': m_kg,
            'acceleration': a
        })
    
    return data

# 初始化 Dash 應用
app = dash.Dash(__name__)
server = app.server  # Railway 部署需要

# 添加 MathJax 支持的自定義 HTML
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <!-- MathJax 配置 -->
    <script>
    window.MathJax = {
        tex: {
            inlineMath: [['$', '$'], ['\\(', '\\)']],
            displayMath: [['$$', '$$'], ['\\[', '\\]']],
            processEscapes: true,
            processEnvironments: true
        },
        options: {
            skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
        }
    };
    </script>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''

# CSS 樣式
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app.external_stylesheets = external_stylesheets

# 應用佈局
app.layout = html.Div([
    # 標題
    html.Div([
        html.H1("滑車-砝碼系統物理模擬器", 
                style={
                    'textAlign': 'center', 
                    'color': '#2c3e50',
                    'marginBottom': '30px',
                    'fontFamily': 'Arial, sans-serif'
                })
    ]),
    
    # 數學理論區域
    html.Div([
        html.H3("理論基礎", style={'color': '#34495e', 'marginBottom': '15px'}),
        
        html.Div([
            # 基本方程
            html.Div([
                html.H5("基本動力學方程："),
                html.P("對砝碼 $m$："),
                html.Div("$$mg - T = ma$$", style={'fontSize': '18px', 'margin': '10px 0'}),
                
                html.P("對滑車 $M$："),
                html.Div("$$T - Mg\\sin\\theta - f = Ma$$", style={'fontSize': '18px', 'margin': '10px 0'}),
            ], className='six columns'),
            
            # 解析解
            html.Div([
                html.H5("系統加速度："),
                html.Div("$$a = \\frac{mg - Mg\\sin\\theta - f}{M + m}$$", 
                        style={'fontSize': '20px', 'margin': '15px 0', 'color': '#e74c3c'}),
                
                html.H5("臨界質量："),
                html.Div("$$m_+ = \\frac{Mg\\sin\\theta + f}{g}$$", 
                        style={'fontSize': '16px', 'margin': '10px 0'}),
                html.Div("$$m_- = \\frac{Mg\\sin\\theta - f}{g}$$", 
                        style={'fontSize': '16px', 'margin': '10px 0'}),
            ], className='six columns')
        ], className='row')
        
    ], style={
        'margin': '20px', 
        'padding': '20px', 
        'backgroundColor': '#f0f8ff', 
        'borderRadius': '10px',
        'border': '2px solid #3498db'
    }),
    
    # 控制面板
    html.Div([
        html.H3("參數控制", style={'color': '#34495e', 'marginBottom': '20px'}),
        
        # 第一行控制項
        html.Div([
            html.Div([
                html.Label("滑車質量 M (g):", 
                          style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.Slider(
                    id='mass-M',
                    min=50, max=500, step=10, value=200,
                    marks={i: f'{i}g' for i in range(50, 551, 100)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                html.Div(id='mass-M-output', style={'marginTop': '10px'})
            ], className='six columns'),
            
            html.Div([
                html.Label("斜面角度 θ (°):", 
                          style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.Slider(
                    id='theta',
                    min=0, max=60, step=5, value=30,
                    marks={i: f'{i}°' for i in range(0, 61, 15)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                html.Div(id='theta-output', style={'marginTop': '10px'})
            ], className='six columns')
        ], className='row'),
        
        # 第二行控制項
        html.Div([
            html.Div([
                html.Label("摩擦力 f (N):", 
                          style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.Slider(
                    id='friction',
                    min=0, max=2, step=0.1, value=0.5,
                    marks={i: f'{i:.1f}N' for i in np.arange(0, 2.1, 0.5)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                html.Div(id='friction-output', style={'marginTop': '10px'})
            ], className='six columns'),
            
            html.Div([
                html.Label("質量範圍 (g):", 
                          style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.RangeSlider(
                    id='mass-range',
                    min=10, max=500, step=10,
                    value=[10, 300],
                    marks={i: f'{i}' for i in range(0, 501, 100)},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], className='six columns')
        ], className='row', style={'marginTop': '30px'})
        
    ], style={'margin': '20px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}),
    
    # 主要內容區域
    html.Div([
        # 左側：關鍵參數和當前狀態
        html.Div([
            html.H3("系統參數", style={'color': '#34495e'}),
            html.Div(id='key-parameters', 
                    style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #dee2e6'}),
            
            html.H3("物理解釋", style={'color': '#34495e', 'marginTop': '20px'}),
            html.Div(id='physics-explanation',
                    style={'backgroundColor': '#e3f2fd', 'padding': '15px', 'borderRadius': '5px'}),
            
            # 當前參數的公式
            html.H3("當前公式", style={'color': '#34495e', 'marginTop': '20px'}),
            html.Div(id='current-formulas',
                    style={'backgroundColor': '#fff3cd', 'padding': '15px', 'borderRadius': '5px'})
        ], className='four columns'),
        
        # 右側：a-m 關係圖
        html.Div([
            html.H3("加速度-質量關係圖", style={'color': '#34495e'}),
            dcc.Graph(
                id='am-plot',
                config={'displayModeBar': True, 'toImageButtonOptions': {'format': 'png'}}
            )
        ], className='eight columns')
    ], className='row', style={'margin': '20px'}),
    
    # 數據表格
    html.Div([
        html.H3("數據表格", style={'color': '#34495e', 'marginBottom': '15px'}),
        dash_table.DataTable(
            id='data-table',
            columns=[
                {"name": "砝碼質量 (g)", "id": "mass_g", "type": "numeric", "format": {"specifier": ".0f"}},
                {"name": "加速度 (m/s²)", "id": "acceleration", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "運動狀態", "id": "motion_state", "type": "text"}
            ],
            style_cell={'textAlign': 'center', 'padding': '10px'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{motion_state} = 向上運動'},
                    'backgroundColor': '#d4edda',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{motion_state} = 向下運動'},
                    'backgroundColor': '#f8d7da',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{motion_state} = 平衡狀態'},
                    'backgroundColor': '#fff3cd',
                    'color': 'black',
                }
            ],
            page_size=10,
            sort_action="native"
        )
    ], style={'margin': '20px'}),
    
    # 隱藏的 div 用於觸發 MathJax 重新渲染
    html.Div(id='mathjax-trigger', style={'display': 'none'})
])

# 回調函數：更新參數顯示
@callback(
    [Output('mass-M-output', 'children'),
     Output('theta-output', 'children'),
     Output('friction-output', 'children')],
    [Input('mass-M', 'value'),
     Input('theta', 'value'),
     Input('friction', 'value')]
)
def update_parameter_display(M, theta, f):
    return (
        f"當前值: {M} g",
        f"當前值: {theta}°",
        f"當前值: {f:.1f} N"
    )

# 主回調函數：更新所有圖表和數據
@callback(
    [Output('am-plot', 'figure'),
     Output('key-parameters', 'children'),
     Output('physics-explanation', 'children'),
     Output('current-formulas', 'children'),
     Output('data-table', 'data')],
    [Input('mass-M', 'value'),
     Input('theta', 'value'),
     Input('friction', 'value'),
     Input('mass-range', 'value')]
)
def update_simulation(M, theta, f, mass_range):
    # 統一單位轉換
    M_kg = M / 1000  # 滑車質量轉換為 kg
    
    # 計算臨界質量（正確的單位）
    m_plus_kg, m_minus_kg = calculate_critical_masses(M_kg, theta, f)  # 傳入 kg
    m_plus_g = m_plus_kg * 1000  # 轉換回 g 顯示
    m_minus_g = m_minus_kg * 1000
    
    # 生成數據
    data_points = generate_data_points(M, theta, f, mass_range[0], mass_range[1], 100)
    
    # 創建圖表
    fig = go.Figure()
    
    # 主曲線
    x_vals = [d['mass_g'] for d in data_points]
    y_vals = [d['acceleration'] for d in data_points]
    
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='lines',
        name='a-m 關係',
        line=dict(color='#3498db', width=3)
    ))
    
    # 添加臨界線
    if m_minus_g >= mass_range[0] and m_minus_g <= mass_range[1]:
        fig.add_vline(
            x=m_minus_g, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"m- = {m_minus_g:.1f}g",
            annotation_position="top"
        )
    
    if m_plus_g >= mass_range[0] and m_plus_g <= mass_range[1]:
        fig.add_vline(
            x=m_plus_g, 
            line_dash="dash", 
            line_color="green",
            annotation_text=f"m+ = {m_plus_g:.1f}g",
            annotation_position="top"
        )
    
    # 添加零線
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    
    # 圖表樣式
    fig.update_layout(
        title=r"$\text{滑車加速度與砝碼質量的關係：} a = f(m, M, \theta, f)$",
        xaxis_title=r"$m \text{ (砝碼質量, g)}$",
        yaxis_title=r"$a \text{ (加速度, m/s²)}$",
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    # 關鍵參數顯示
    theta_rad = np.radians(theta)
    mg_sin = M_kg * 9.8 * np.sin(theta_rad)  # 使用 M_kg
    
    parameters = html.Div([
        html.P(f"m+ = {m_plus_g:.1f} g", style={'margin': '5px 0'}),
        html.P(f"m- = {m_minus_g:.1f} g", style={'margin': '5px 0'}),
        html.P(f"Mg sin θ = {mg_sin:.3f} N", style={'margin': '5px 0'}),
        html.P(f"摩擦力 = {f:.1f} N", style={'margin': '5px 0'}),
        html.P(f"平衡區間 = {abs(m_plus_g - m_minus_g):.1f} g", style={'margin': '5px 0'})
    ])
    
    # 物理解釋
    if m_plus_g - m_minus_g < 10:
        explanation_text = "摩擦力很小，系統容易運動"
    elif m_plus_g - m_minus_g > 100:
        explanation_text = "摩擦力很大，需要較大質量差才能運動"
    else:
        explanation_text = "正常的摩擦力範圍"
        
    explanation = html.Div([
        html.P("系統分析:", style={'fontWeight': 'bold'}),
        html.P(f"• m < {m_minus_g:.1f}g: 滑車向下滑動", style={'margin': '5px 0'}),
        html.P(f"• {m_minus_g:.1f}g < m < {m_plus_g:.1f}g: 平衡狀態", style={'margin': '5px 0'}),
        html.P(f"• m > {m_plus_g:.1f}g: 滑車向上運動", style={'margin': '5px 0'}),
        html.P(explanation_text, style={'margin': '10px 0', 'fontStyle': 'italic'})
    ])
    
    # 當前參數的數學公式
    current_formulas = html.Div([
        html.P("當前參數代入：", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
        html.Div(f"$$M = {M}\\text{{g}} = {M_kg:.3f}\\text{{kg}}, \\quad \\theta = {theta}°, \\quad f = {f}\\text{{N}}$$"),
        html.Div(f"$$m_+ = \\frac{{{M_kg:.3f} \\times 9.8 \\times \\sin({theta}°) + {f}}}{{9.8}} = {m_plus_g:.1f}\\text{{g}}$$"),
        html.Div(f"$$m_- = \\frac{{{M_kg:.3f} \\times 9.8 \\times \\sin({theta}°) - {f}}}{{9.8}} = {m_minus_g:.1f}\\text{{g}}$$"),
    ])
    
    # 生成表格數據
    table_data = []
    selected_indices = np.linspace(0, len(data_points)-1, 20, dtype=int)
    
    for i in selected_indices:
        d = data_points[i]
        if d['acceleration'] > 0.01:
            motion = "向上運動"
        elif d['acceleration'] < -0.01:
            motion = "向下運動"  
        else:
            motion = "平衡狀態"
            
        table_data.append({
            'mass_g': round(d['mass_g'], 1),
            'acceleration': round(d['acceleration'], 3),
            'motion_state': motion
        })
    
    return fig, parameters, explanation, current_formulas, table_data

# 客戶端回調：重新渲染 MathJax
app.clientside_callback(
    """
    function(formulas) {
        setTimeout(function() {
            if (window.MathJax) {
                MathJax.typesetPromise().then(function() {
                    console.log('MathJax re-rendered');
                });
            }
        }, 100);
        return '';
    }
    """,
    Output('mathjax-trigger', 'children'),
    [Input('current-formulas', 'children'),
     Input('key-parameters', 'children')]
)

# Railway 兼容的主程序
if __name__ == "__main__":
    # 獲取端口
    port_str = os.environ.get("PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning(f"Invalid PORT value: {port_str!r}, falling back to 8080")
        port = 8080

    # 檢查是否為生產環境
    debug_mode = os.environ.get("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting Dash app on host=0.0.0.0, port={port}, debug={debug_mode}")
    
    # 使用 Dash 的 run_server 方法
    app.run_server(
        host="0.0.0.0", 
        port=port, 
        debug=debug_mode
    )