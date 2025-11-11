import dash
from dash import html, Input, Output, State, dcc
import dash_bootstrap_components as dbc
from model_serving_utils import generate_hooks, generate_thumbnails
import threading
import time

class HookGenerator:
    def __init__(self, app, endpoint_name):
        self.app = app
        self.endpoint_name = endpoint_name
        self.generation_status = {}  # Track generation status
        self.layout = self._create_layout()
        self._create_callbacks()
        self._add_custom_css()

    def _create_layout(self):
        return html.Div([
            html.H1('🎯 Databricks Hook Generator', className='hook-title mb-4'),
            html.P([
                'Transform your technical blog into click-magnet titles and promise-driven subtitles. ',
                'Built for senior data engineers, platform engineers, and data/ML architects.'
            ], className='hook-subtitle mb-4'),
            
            dbc.Card([
                dbc.CardHeader([
                    html.H5('📝 Blog Content Input', className='mb-0')
                ]),
                dbc.CardBody([
                    dbc.Textarea(
                        id='blog-input',
                        placeholder='Paste your blog content here (draft, outline, or final article)...',
                        className='blog-textarea',
                        style={'height': '400px', 'fontSize': '14px'}
                    ),
                    html.Div([
                        dbc.Button(
                            '✨ Generate Hooks',
                            id='generate-button',
                            color='success',
                            size='lg',
                            className='me-2 mt-3',
                            n_clicks=0
                        ),
                        dbc.Button(
                            '🎨 Generate Thumbnails',
                            id='generate-thumbnail-button',
                            color='primary',
                            size='lg',
                            className='me-2 mt-3',
                            n_clicks=0
                        ),
                        dbc.Button(
                            '🗑️ Clear',
                            id='clear-button',
                            color='secondary',
                            size='lg',
                            className='mt-3',
                            n_clicks=0
                        ),
                    ], className='d-flex'),
                ])
            ], className='mb-4'),
            
            # Loading indicator
            html.Div(id='loading-container', children=[
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Spinner(color='primary', size='lg'),
                            html.H4('🎨 Generating your hooks...', className='mt-3 text-center'),
                            html.P('This may take 10-30 seconds', className='text-center text-muted')
                        ], className='text-center p-4')
                    ])
                ])
            ], style={'display': 'none'}),
            
            # Hooks Output container
            html.Div(id='output-container', children=[
                dbc.Card([
                    dbc.CardHeader([
                        html.H5('✨ Generated Hooks', className='mb-0 d-inline'),
                        dbc.Button(
                            '📋 Copy All',
                            id='copy-button',
                            color='link',
                            size='sm',
                            className='float-end'
                        ),
                    ]),
                    dbc.CardBody([
                        html.Pre(
                            id='output-text',
                            className='output-text',
                            style={'whiteSpace': 'pre-wrap', 'fontSize': '14px'}
                        )
                    ])
                ], className='output-card')
            ], style={'display': 'none'}),
            
            # Thumbnails Output container
            html.Div(id='thumbnail-output-container', children=[
                dbc.Card([
                    dbc.CardHeader([
                        html.H5('🎨 Generated Thumbnails', className='mb-0 d-inline'),
                        dbc.Button(
                            '📋 Copy Concepts',
                            id='copy-thumbnail-button',
                            color='link',
                            size='sm',
                            className='float-end'
                        ),
                    ]),
                    dbc.CardBody([
                        html.Div(id='thumbnail-output-text')
                    ])
                ], className='output-card')
            ], style={'display': 'none'}),
            
            # Stores for state management
            dcc.Store(id='output-store'),
            dcc.Store(id='generation-trigger'),
            dcc.Store(id='generation-result'),
            dcc.Store(id='thumbnail-output-store'),
            dcc.Store(id='thumbnail-generation-trigger'),
            dcc.Store(id='thumbnail-generation-result'),
            
            # Interval for checking generation status
            dcc.Interval(id='check-interval', interval=500, disabled=True, n_intervals=0),
            dcc.Interval(id='thumbnail-check-interval', interval=500, disabled=True, n_intervals=0),
            
            html.Div(id='copy-feedback', className='copy-feedback'),
            html.Div(id='dummy-output', style={'display': 'none'})
        ], className='hook-container p-4')

    def _create_callbacks(self):
        # Callback 1: Start generation (non-blocking)
        @self.app.callback(
            Output('generation-trigger', 'data'),
            Output('loading-container', 'style'),
            Output('output-container', 'style', allow_duplicate=True),
            Output('check-interval', 'disabled'),
            Output('check-interval', 'n_intervals'),
            Input('generate-button', 'n_clicks'),
            State('blog-input', 'value'),
            prevent_initial_call=True
        )
        def start_generation(n_clicks, blog_content):
            if not blog_content or not blog_content.strip():
                # Show error in output
                return (
                    None,
                    {'display': 'none'},
                    {'display': 'block'},
                    True,
                    0
                )
            
            if n_clicks > 0:
                # Generate unique ID for this generation
                gen_id = f"gen_{n_clicks}_{time.time()}"
                
                # Start generation in background thread
                def generate_in_background():
                    try:
                        result = generate_hooks(self.endpoint_name, blog_content)
                        self.generation_status[gen_id] = {'status': 'complete', 'result': result}
                    except Exception as e:
                        self.generation_status[gen_id] = {'status': 'error', 'result': f'❌ Error: {str(e)}'}
                
                self.generation_status[gen_id] = {'status': 'generating', 'result': None}
                thread = threading.Thread(target=generate_in_background, daemon=True)
                thread.start()
                
                # Show loading, hide output, enable interval checking
                return (
                    gen_id,
                    {'display': 'block'},
                    {'display': 'none'},
                    False,  # Enable interval
                    0  # Reset interval counter
                )
            
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Callback 2: Check generation status periodically
        @self.app.callback(
            Output('generation-result', 'data'),
            Output('check-interval', 'disabled', allow_duplicate=True),
            Input('check-interval', 'n_intervals'),
            State('generation-trigger', 'data'),
            prevent_initial_call=True
        )
        def check_generation_status(n_intervals, gen_id):
            if not gen_id or gen_id not in self.generation_status:
                return None, True
            
            status_info = self.generation_status[gen_id]
            
            if status_info['status'] in ['complete', 'error']:
                # Generation is done, disable interval and return result
                result = status_info['result']
                # Clean up
                del self.generation_status[gen_id]
                return result, True
            
            # Still generating, keep checking
            return None, False

        # Callback 3: Display results when ready
        @self.app.callback(
            Output('output-text', 'children'),
            Output('loading-container', 'style', allow_duplicate=True),
            Output('output-container', 'style', allow_duplicate=True),
            Output('output-store', 'data'),
            Input('generation-result', 'data'),
            prevent_initial_call=True
        )
        def display_results(result):
            if result is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            return (
                result,
                {'display': 'none'},  # Hide loading
                {'display': 'block'},  # Show output
                result
            )

        # Callback 4: Clear button
        @self.app.callback(
            Output('blog-input', 'value'),
            Output('output-container', 'style', allow_duplicate=True),
            Output('generation-result', 'data', allow_duplicate=True),
            Input('clear-button', 'n_clicks'),
            prevent_initial_call=True
        )
        def clear_all(n_clicks):
            if n_clicks:
                return '', {'display': 'none'}, None
            return dash.no_update, dash.no_update, dash.no_update

        # Client-side callback for copy hooks functionality
        self.app.clientside_callback(
            """
            function(n_clicks, output_data) {
                if (n_clicks > 0 && output_data) {
                    navigator.clipboard.writeText(output_data).then(function() {
                        var feedback = document.getElementById('copy-feedback');
                        if (feedback) {
                            feedback.textContent = '✓ Copied to clipboard!';
                            feedback.style.display = 'block';
                            setTimeout(function() {
                                feedback.style.display = 'none';
                            }, 2000);
                        }
                    });
                }
                return '';
            }
            """,
            Output('dummy-output', 'children'),
            Input('copy-button', 'n_clicks'),
            State('output-store', 'data'),
            prevent_initial_call=True
        )

        # ========== THUMBNAIL GENERATION CALLBACKS ==========
        
        # Callback 5: Start thumbnail generation (non-blocking)
        @self.app.callback(
            Output('thumbnail-generation-trigger', 'data'),
            Output('loading-container', 'style', allow_duplicate=True),
            Output('thumbnail-output-container', 'style', allow_duplicate=True),
            Output('thumbnail-check-interval', 'disabled'),
            Output('thumbnail-check-interval', 'n_intervals'),
            Input('generate-thumbnail-button', 'n_clicks'),
            State('blog-input', 'value'),
            prevent_initial_call=True
        )
        def start_thumbnail_generation(n_clicks, blog_content):
            if not blog_content or not blog_content.strip():
                return (
                    None,
                    {'display': 'none'},
                    {'display': 'block'},
                    True,
                    0
                )
            
            if n_clicks > 0:
                gen_id = f"thumb_{n_clicks}_{time.time()}"
                
                def generate_in_background():
                    try:
                        result = generate_thumbnails(self.endpoint_name, blog_content)
                        self.generation_status[gen_id] = {'status': 'complete', 'result': result}
                    except Exception as e:
                        self.generation_status[gen_id] = {'status': 'error', 'result': f'❌ Error: {str(e)}'}
                
                self.generation_status[gen_id] = {'status': 'generating', 'result': None}
                thread = threading.Thread(target=generate_in_background, daemon=True)
                thread.start()
                
                return (
                    gen_id,
                    {'display': 'block'},
                    {'display': 'none'},
                    False,  # Enable interval
                    0
                )
            
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Callback 6: Check thumbnail generation status periodically
        @self.app.callback(
            Output('thumbnail-generation-result', 'data'),
            Output('thumbnail-check-interval', 'disabled', allow_duplicate=True),
            Input('thumbnail-check-interval', 'n_intervals'),
            State('thumbnail-generation-trigger', 'data'),
            prevent_initial_call=True
        )
        def check_thumbnail_generation_status(n_intervals, gen_id):
            if not gen_id or gen_id not in self.generation_status:
                return None, True
            
            status_info = self.generation_status[gen_id]
            
            if status_info['status'] in ['complete', 'error']:
                result = status_info['result']
                del self.generation_status[gen_id]
                return result, True
            
            return None, False

        # Callback 7: Display thumbnail results with images
        @self.app.callback(
            Output('thumbnail-output-text', 'children'),
            Output('loading-container', 'style', allow_duplicate=True),
            Output('thumbnail-output-container', 'style', allow_duplicate=True),
            Output('thumbnail-output-store', 'data'),
            Input('thumbnail-generation-result', 'data'),
            prevent_initial_call=True
        )
        def display_thumbnail_results(result):
            if result is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            # Parse result to extract concepts and images
            import re
            
            # Split between concepts and images
            parts = result.split("🎨 GENERATED IMAGES")
            concepts_text = parts[0] if len(parts) > 0 else result
            images_section = parts[1] if len(parts) > 1 else ""
            
            # Extract full base64 images
            image_matches = re.findall(r'Image \d+:\n\[BASE64_IMAGE_DATA\]\n(.+?)\n\[END_IMAGE_DATA\]', result, re.DOTALL)
            
            # Build output
            output_children = []
            
            # Add concepts section
            output_children.append(html.Div([
                html.H6("📝 Thumbnail Concepts", style={'marginBottom': '10px', 'fontWeight': 'bold'}),
                html.Pre(concepts_text.strip(), style={
                    'whiteSpace': 'pre-wrap', 
                    'fontSize': '13px',
                    'backgroundColor': '#f8f9fa',
                    'padding': '15px',
                    'borderRadius': '5px',
                    'marginBottom': '20px'
                })
            ]))
            
            # Add generated images if available
            if image_matches:
                output_children.append(html.H6("🖼️ Generated Images", style={
                    'marginTop': '20px',
                    'marginBottom': '15px',
                    'fontWeight': 'bold'
                }))
                
                for idx, img_b64 in enumerate(image_matches, 1):
                    img_b64_clean = img_b64.strip()
                    if img_b64_clean:
                        output_children.append(html.Div([
                            html.P(f"Thumbnail {idx}", style={'fontWeight': '500', 'marginBottom': '10px'}),
                            html.Img(
                                src=f"data:image/png;base64,{img_b64_clean}",
                                style={
                                    'width': '100%',
                                    'maxWidth': '600px',
                                    'borderRadius': '8px',
                                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                                    'marginBottom': '20px'
                                }
                            )
                        ]))
            
            # Store only the concepts text for copying
            store_data = concepts_text.strip()
            
            return (
                output_children,
                {'display': 'none'},  # Hide loading
                {'display': 'block'},  # Show output
                store_data
            )

        # Callback 8: Update clear button to also clear thumbnails
        @self.app.callback(
            Output('thumbnail-output-container', 'style', allow_duplicate=True),
            Output('thumbnail-generation-result', 'data', allow_duplicate=True),
            Input('clear-button', 'n_clicks'),
            prevent_initial_call=True
        )
        def clear_thumbnails(n_clicks):
            if n_clicks:
                return {'display': 'none'}, None
            return dash.no_update, dash.no_update

        # Client-side callback for copy thumbnail functionality
        self.app.clientside_callback(
            """
            function(n_clicks, output_data) {
                if (n_clicks > 0 && output_data) {
                    navigator.clipboard.writeText(output_data).then(function() {
                        var feedback = document.getElementById('copy-feedback');
                        if (feedback) {
                            feedback.textContent = '✓ Thumbnails copied to clipboard!';
                            feedback.style.display = 'block';
                            setTimeout(function() {
                                feedback.style.display = 'none';
                            }, 2000);
                        }
                    });
                }
                return '';
            }
            """,
            Output('dummy-output', 'children', allow_duplicate=True),
            Input('copy-thumbnail-button', 'n_clicks'),
            State('thumbnail-output-store', 'data'),
            prevent_initial_call=True
        )

    def _add_custom_css(self):
        custom_css = '''
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
        
        body {
            font-family: 'DM Sans', sans-serif;
            background: linear-gradient(135deg, #F9F7F4 0%, #EEEDE9 100%);
            min-height: 100vh;
        }
        
        .hook-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .hook-title {
            font-size: 48px;
            font-weight: 700;
            color: #1B3139;
            text-align: center;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .hook-subtitle {
            font-size: 18px;
            color: #2D4550;
            text-align: center;
            max-width: 800px;
            margin: 0 auto 2rem auto;
            line-height: 1.6;
        }
        
        .blog-textarea {
            font-family: 'DM Sans', monospace;
            border-radius: 10px;
            border: 2px solid #DCE0E2;
            padding: 1rem;
            resize: vertical;
        }
        
        .blog-textarea:focus {
            border-color: #FF3621;
            box-shadow: 0 0 0 0.2rem rgba(255, 54, 33, 0.25);
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .card-header {
            background-color: #1B3139;
            color: white;
            border-radius: 15px 15px 0 0 !important;
            padding: 1rem 1.5rem;
            font-weight: 600;
        }
        
        .output-card .card-header {
            background-color: #00A972;
        }
        
        #generate-button {
            background-color: #FF3621;
            border-color: #FF3621;
            font-weight: 600;
            padding: 0.75rem 2rem;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        
        #generate-button:hover {
            background-color: #E62E1C;
            border-color: #E62E1C;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(255, 54, 33, 0.3);
        }
        
        #clear-button {
            border-radius: 25px;
            padding: 0.75rem 2rem;
            font-weight: 600;
        }
        
        #copy-button {
            color: white;
            text-decoration: none;
            font-weight: 600;
        }
        
        #copy-button:hover {
            color: #EEEDE9;
            text-decoration: underline;
        }
        
        .output-text {
            background-color: #F9F7F4;
            padding: 1.5rem;
            border-radius: 10px;
            font-family: 'DM Sans', sans-serif;
            color: #1B3139;
            line-height: 1.8;
            margin: 0;
            min-height: 200px;
        }
        
        .copy-feedback {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #00A972;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            display: none;
            z-index: 9999;
            font-weight: 600;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .spinner-border {
            border-color: #FF3621;
            border-right-color: transparent;
        }
        
        #loading-container {
            text-align: center;
            padding: 3rem;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .hook-title {
                font-size: 32px;
            }
            
            .hook-subtitle {
                font-size: 16px;
            }
            
            .hook-container {
                padding: 1rem;
            }
        }
        '''
        
        self.app.index_string = self.app.index_string.replace(
            '</head>',
            f'<style>{custom_css}</style></head>'
        )
