"""
Real-time Trading Bot Dashboard
Displays live performance metrics, charts, and trade history
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# Dashboard configuration
DASHBOARD_PORT = 8050
UPDATE_INTERVAL = 5000  # 5 seconds

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
STATE_FILE = BASE_DIR / 'bot_state.json'
LOG_FILE = BASE_DIR / 'eurcad_bot.log'


class TradingDashboard:
    """
    Real-time dashboard for EUR/CAD trading bot
    """

    def __init__(self, port=DASHBOARD_PORT):
        self.port = port
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()

    def setup_layout(self):
        """Setup dashboard layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1('EUR/CAD Trading Bot - Live Dashboard',
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 10}),
                html.P('Real-time Performance Monitoring',
                      style={'textAlign': 'center', 'color': '#7f8c8d', 'marginTop': 0}),
            ], style={'backgroundColor': '#ecf0f1', 'padding': '20px', 'marginBottom': '20px'}),

            # Key Metrics Row
            html.Div([
                # Current Capital
                html.Div([
                    html.Div([
                        html.H4('Current Capital', style={'color': '#7f8c8d', 'marginBottom': 5}),
                        html.H2(id='current-capital', children='$0.00',
                               style={'color': '#27ae60', 'marginTop': 0}),
                    ], style={'textAlign': 'center'}),
                ], className='metric-box', style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),

                # Win Rate
                html.Div([
                    html.Div([
                        html.H4('Win Rate', style={'color': '#7f8c8d', 'marginBottom': 5}),
                        html.H2(id='win-rate', children='0%',
                               style={'color': '#3498db', 'marginTop': 0}),
                    ], style={'textAlign': 'center'}),
                ], className='metric-box', style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),

                # Total Trades
                html.Div([
                    html.Div([
                        html.H4('Total Trades', style={'color': '#7f8c8d', 'marginBottom': 5}),
                        html.H2(id='total-trades', children='0',
                               style={'color': '#9b59b6', 'marginTop': 0}),
                    ], style={'textAlign': 'center'}),
                ], className='metric-box', style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),

                # Open Positions
                html.Div([
                    html.Div([
                        html.H4('Open Positions', style={'color': '#7f8c8d', 'marginBottom': 5}),
                        html.H2(id='open-positions', children='0',
                               style={'color': '#e67e22', 'marginTop': 0}),
                    ], style={'textAlign': 'center'}),
                ], className='metric-box', style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),
            ], style={'display': 'flex', 'flexWrap': 'wrap'}),

            # Strategy Info Row
            html.Div([
                # Market Regime
                html.Div([
                    html.H4('Market Regime', style={'color': '#7f8c8d', 'marginBottom': 10}),
                    html.H3(id='market-regime', children='N/A',
                           style={'color': '#2c3e50', 'marginTop': 0}),
                ], style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'textAlign': 'center'
                }),

                # Active Strategy
                html.Div([
                    html.H4('Active Strategy', style={'color': '#7f8c8d', 'marginBottom': 10}),
                    html.H3(id='active-strategy', children='N/A',
                           style={'color': '#2c3e50', 'marginTop': 0}),
                ], style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'textAlign': 'center'
                }),

                # Bot Status
                html.Div([
                    html.H4('Bot Status', style={'color': '#7f8c8d', 'marginBottom': 10}),
                    html.H3(id='bot-status', children='Stopped',
                           style={'color': '#e74c3c', 'marginTop': 0}),
                ], style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'textAlign': 'center'
                }),
            ], style={'display': 'flex', 'flexWrap': 'wrap'}),

            # Charts Row
            html.Div([
                # Equity Curve
                html.Div([
                    html.H3('Equity Curve', style={'color': '#2c3e50', 'textAlign': 'center'}),
                    dcc.Graph(id='equity-curve', config={'displayModeBar': False},
                             style={'height': '300px'}),
                ], style={
                    'flex': 2, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'minHeight': '380px'
                }),

                # Win/Loss Pie Chart
                html.Div([
                    html.H3('Win/Loss Distribution', style={'color': '#2c3e50', 'textAlign': 'center'}),
                    dcc.Graph(id='win-loss-pie', config={'displayModeBar': False},
                             style={'height': '300px'}),
                ], style={
                    'flex': 1, 'backgroundColor': 'white', 'padding': '20px',
                    'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'minHeight': '380px'
                }),
            ], style={'display': 'flex', 'flexWrap': 'wrap'}),

            # Recent Trades Table
            html.Div([
                html.H3('Recent Trades', style={'color': '#2c3e50', 'marginBottom': 15}),
                html.Div(id='recent-trades-table'),
            ], style={
                'backgroundColor': 'white', 'padding': '20px',
                'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }),

            # Bot Logs
            html.Div([
                html.H3('Bot Logs (Last 50 entries)', style={'color': '#2c3e50', 'marginBottom': 15}),
                html.Div(id='bot-logs', style={
                    'backgroundColor': '#2c3e50',
                    'color': '#ecf0f1',
                    'padding': '15px',
                    'borderRadius': '5px',
                    'fontFamily': 'Consolas, Monaco, monospace',
                    'fontSize': '12px',
                    'height': '400px',
                    'overflowY': 'auto',
                    'whiteSpace': 'pre-wrap',
                    'lineHeight': '1.5'
                }),
            ], style={
                'backgroundColor': 'white', 'padding': '20px',
                'margin': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }),

            # Auto-refresh component
            dcc.Interval(
                id='interval-component',
                interval=UPDATE_INTERVAL,
                n_intervals=0
            ),

            # Last Update Time
            html.Div([
                html.P(id='last-update', children='Last updated: Never',
                      style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '12px'}),
            ], style={'marginTop': '20px'}),

        ], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f5f5f5', 'padding': '20px'})

    def setup_callbacks(self):
        """Setup dashboard callbacks for real-time updates"""

        @self.app.callback(
            [
                Output('current-capital', 'children'),
                Output('win-rate', 'children'),
                Output('total-trades', 'children'),
                Output('open-positions', 'children'),
                Output('market-regime', 'children'),
                Output('active-strategy', 'children'),
                Output('bot-status', 'children'),
                Output('bot-status', 'style'),
                Output('equity-curve', 'figure'),
                Output('win-loss-pie', 'figure'),
                Output('recent-trades-table', 'children'),
                Output('bot-logs', 'children'),
                Output('last-update', 'children'),
            ],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            """Update all dashboard components"""

            # Read bot state
            state = self.read_bot_state()

            if not state:
                # No state file - bot not running
                logs_display = self.read_logs()
                return (
                    '$0.00', '0%', '0', '0', 'N/A', 'N/A', 'Stopped',
                    {'color': '#e74c3c', 'marginTop': 0},
                    self.create_empty_equity_curve(),
                    self.create_empty_pie_chart(),
                    html.P('No data available. Start the bot to see trades.',
                          style={'textAlign': 'center', 'color': '#7f8c8d'}),
                    logs_display,
                    f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                )

            # Extract metrics
            capital = state.get('current_capital', 0)
            win_rate = state.get('win_rate', 0)
            total_trades = state.get('total_trades', 0)
            open_positions = state.get('open_positions', 0)
            market_regime = state.get('market_regime', 'N/A')
            active_strategy = state.get('active_strategy', 'N/A')
            bot_status = state.get('status', 'Stopped')
            equity_curve = state.get('equity_curve', [capital])
            trades = state.get('trades', [])

            # Status color
            status_style = {
                'marginTop': 0,
                'color': '#27ae60' if bot_status == 'Running' else '#e74c3c'
            }

            # Format values
            capital_text = f'${capital:,.2f}'
            win_rate_text = f'{win_rate:.1f}%'

            # Create charts
            equity_fig = self.create_equity_curve(equity_curve)
            pie_fig = self.create_win_loss_pie(trades)

            # Create trades table
            trades_table = self.create_trades_table(trades)

            # Read logs
            logs_display = self.read_logs()

            return (
                capital_text, win_rate_text, str(total_trades), str(open_positions),
                market_regime, active_strategy, bot_status, status_style,
                equity_fig, pie_fig, trades_table, logs_display,
                f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )

    def read_bot_state(self):
        """Read bot state from JSON file"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading bot state: {e}")
        return None

    def read_logs(self, num_lines=50):
        """Read last N lines from log file with color coding"""
        try:
            if not LOG_FILE.exists():
                return "Log file not found. Bot may not be running yet."

            # Read last N lines
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-num_lines:] if len(lines) > num_lines else lines

            # Create formatted log entries with color coding
            log_elements = []
            for line in last_lines:
                line = line.strip()
                if not line:
                    continue

                # Color code based on log level
                if ' - ERROR - ' in line or ' - CRITICAL - ' in line:
                    color = '#e74c3c'  # Red
                elif ' - WARNING - ' in line:
                    color = '#f39c12'  # Orange
                elif ' - INFO - ' in line:
                    color = '#3498db'  # Blue
                else:
                    color = '#ecf0f1'  # Light gray

                log_elements.append(
                    html.Div(line, style={'color': color, 'marginBottom': '2px'})
                )

            if not log_elements:
                return "No logs available yet."

            return html.Div(log_elements)

        except Exception as e:
            return f"Error reading logs: {e}"

    def create_equity_curve(self, equity_data):
        """Create equity curve chart"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=equity_data,
            mode='lines',
            name='Equity',
            line=dict(color='#27ae60', width=2),
            fill='tozeroy',
            fillcolor='rgba(39, 174, 96, 0.1)'
        ))

        fig.update_layout(
            xaxis_title='Trade Number',
            yaxis_title='Capital ($)',
            hovermode='x unified',
            plot_bgcolor='white',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(showgrid=True, gridcolor='#ecf0f1'),
            yaxis=dict(showgrid=True, gridcolor='#ecf0f1'),
            autosize=False,
            uirevision='constant',  # Prevent layout changes on updates
        )

        return fig

    def create_empty_equity_curve(self):
        """Create empty equity curve"""
        fig = go.Figure()
        fig.add_annotation(
            text="No data yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#7f8c8d")
        )
        fig.update_layout(
            height=300,
            plot_bgcolor='white',
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False),
            autosize=False,
            uirevision='constant',
        )
        return fig

    def create_win_loss_pie(self, trades):
        """Create win/loss pie chart"""
        if not trades:
            return self.create_empty_pie_chart()

        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = len(trades) - wins

        fig = go.Figure(data=[go.Pie(
            labels=['Wins', 'Losses'],
            values=[wins, losses],
            marker=dict(colors=['#27ae60', '#e74c3c']),
            hole=0.4,
            textinfo='label+percent',
            textfont=dict(size=14),
        )])

        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            autosize=False,
            uirevision='constant',
        )

        return fig

    def create_empty_pie_chart(self):
        """Create empty pie chart"""
        fig = go.Figure()
        fig.add_annotation(
            text="No trades yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#7f8c8d")
        )
        fig.update_layout(
            height=300,
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False),
            autosize=False,
            uirevision='constant',
        )
        return fig

    def create_trades_table(self, trades):
        """Create recent trades table"""
        if not trades:
            return html.P('No trades yet',
                         style={'textAlign': 'center', 'color': '#7f8c8d', 'padding': '20px'})

        # Get last 10 trades
        recent_trades = trades[-10:][::-1]  # Reverse to show newest first

        # Create table
        table_header = [
            html.Thead(html.Tr([
                html.Th('Time', style={'padding': '10px', 'textAlign': 'left'}),
                html.Th('Type', style={'padding': '10px', 'textAlign': 'left'}),
                html.Th('Entry', style={'padding': '10px', 'textAlign': 'right'}),
                html.Th('Exit', style={'padding': '10px', 'textAlign': 'right'}),
                html.Th('P&L', style={'padding': '10px', 'textAlign': 'right'}),
                html.Th('Result', style={'padding': '10px', 'textAlign': 'center'}),
            ]))
        ]

        table_rows = []
        for trade in recent_trades:
            pnl = trade.get('pnl', 0)
            pnl_color = '#27ae60' if pnl > 0 else '#e74c3c'
            result_text = 'WIN' if pnl > 0 else 'LOSS'
            result_color = '#27ae60' if pnl > 0 else '#e74c3c'

            row = html.Tr([
                html.Td(trade.get('exit_time', 'N/A')[:16], style={'padding': '10px'}),
                html.Td(trade.get('type', 'N/A').upper(), style={'padding': '10px'}),
                html.Td(f"{trade.get('entry_price', 0):.5f}", style={'padding': '10px', 'textAlign': 'right'}),
                html.Td(f"{trade.get('exit_price', 0):.5f}", style={'padding': '10px', 'textAlign': 'right'}),
                html.Td(f"${pnl:.2f}", style={'padding': '10px', 'textAlign': 'right', 'color': pnl_color, 'fontWeight': 'bold'}),
                html.Td(result_text, style={'padding': '10px', 'textAlign': 'center', 'color': result_color, 'fontWeight': 'bold'}),
            ], style={'borderBottom': '1px solid #ecf0f1'})

            table_rows.append(row)

        table_body = [html.Tbody(table_rows)]

        return html.Table(
            table_header + table_body,
            style={'width': '100%', 'borderCollapse': 'collapse'}
        )

    def run(self, show_banner=True):
        """Run dashboard server"""
        if show_banner:
            print(f"""
        =========================================
           EUR/CAD BOT DASHBOARD STARTED
        =========================================
           Open your browser and go to:
           http://localhost:{self.port}

           Dashboard will auto-refresh every 5s
           Press Ctrl+C to stop
        =========================================
        """)

        # Suppress Flask startup messages
        import logging as flask_logging
        log = flask_logging.getLogger('werkzeug')
        log.setLevel(flask_logging.ERROR)

        self.app.run(debug=False, port=self.port, host='0.0.0.0')


def main():
    """Main entry point"""
    dashboard = TradingDashboard(port=8050)
    dashboard.run()


if __name__ == "__main__":
    main()
