# PDF to Editable Web Converter

A modern web application that converts PDF documents into beautiful, editable web pages with rich formatting tools similar to Microsoft Word.

## Features

### 🎯 Core Functionality
- **PDF Upload**: Drag & drop or click to upload PDF files
- **Smart Conversion**: Automatically detects and preserves:
  - Text content with hierarchical structure
  - Tables with professional formatting
  - Images and diagrams
  - Document sections and navigation

### ✏️ Rich Editor
- **Word-like Toolbar**: Complete formatting tools including:
  - **Text Formatting**: Bold, Italic, Underline
  - **Alignment**: Left, Center, Right, Justify
  - **Lists**: Bullet points and numbered lists
  - **Font Controls**: Size and family selection
  - **Colors**: Text and background color pickers
  - **Links**: Insert and edit hyperlinks
  - **Images**: Insert images from URLs
  - **Tables**: Create and edit tables with custom dimensions

### 📱 Modern Interface
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Beautiful UI**: Modern gradient design with smooth animations
- **Real-time Preview**: See changes as you edit
- **Auto-save**: Automatic saving with status notifications

### 🔄 Workflow
1. **Upload**: Drag & drop your PDF file
2. **Convert**: Click "Convert PDF" to process
3. **View**: Preview the converted document
4. **Edit**: Use the rich editor to modify content
5. **Save**: Save your changes
6. **Download**: Download the final HTML file

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup
1. **Clone or download** the project files
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   python app.py
   ```
4. **Open your browser** and go to: `http://localhost:5000`

## Usage

### Step 1: Upload PDF
- Drag and drop your PDF file onto the upload area
- Or click to browse and select a file
- Supported format: PDF only

### Step 2: Convert
- Click the "Convert PDF" button
- Wait for the conversion process to complete
- The system will automatically detect tables, images, and document structure

### Step 3: View & Edit
- **View**: Click "View" to see the converted document in read-only mode
- **Edit**: Click "Edit" to open the rich text editor
- **Download**: Click "Download" to save the HTML file

### Step 4: Rich Editing
In the editor, you can:
- **Format Text**: Use the toolbar for bold, italic, underline
- **Align Content**: Left, center, right, or justify text
- **Create Lists**: Bullet points or numbered lists
- **Insert Tables**: Create tables with custom rows and columns
- **Add Links**: Insert hyperlinks
- **Insert Images**: Add images from URLs
- **Change Fonts**: Select font family and size
- **Apply Colors**: Change text and background colors

### Step 5: Save Changes
- Click the "Save" button to preserve your edits
- Changes are automatically saved to the server
- You can continue editing or download the final version

## File Structure

```
├── app.py                 # Main Flask application
├── pdf_to_webpage.py     # PDF conversion logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── index.html       # Main upload page
│   ├── viewer.html      # Document viewer
│   └── editor.html      # Rich text editor
├── uploads/             # Temporary PDF storage
└── outputs/             # Generated HTML files
```

## Technical Details

### Backend
- **Flask**: Web framework for the application
- **PyMuPDF**: PDF processing and text extraction
- **Pillow**: Image processing and manipulation
- **Werkzeug**: File upload handling

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with gradients and animations
- **JavaScript**: Interactive functionality and AJAX requests
- **Font Awesome**: Icons for the interface

### Features
- **ContentEditable**: Rich text editing using browser's native capabilities
- **execCommand**: Formatting commands for text manipulation
- **File Upload**: Drag & drop with progress indication
- **Responsive Design**: Mobile-first approach
- **Real-time Feedback**: Status messages and loading indicators

## Browser Compatibility

- **Chrome**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support

## Limitations

- **File Size**: Maximum 50MB per PDF
- **Format**: PDF files only
- **Complex Layouts**: Very complex PDF layouts may not convert perfectly
- **Fonts**: Some custom fonts may not render exactly as in the original

## Troubleshooting

### Common Issues

1. **"No module named 'PIL'"**
   - Solution: `pip install Pillow`

2. **"No module named 'fitz'"**
   - Solution: `pip install PyMuPDF`

3. **Upload fails**
   - Check file size (max 50MB)
   - Ensure file is a valid PDF
   - Check internet connection

4. **Editor not working**
   - Use a modern browser (Chrome, Firefox, Safari, Edge)
   - Enable JavaScript in your browser

### Getting Help

If you encounter issues:
1. Check the browser console for error messages
2. Ensure all dependencies are installed
3. Verify the Flask server is running
4. Check file permissions for uploads and outputs directories

## Development

### Running in Development Mode
```bash
python app.py
```

### Customizing Styles
Edit the CSS in the template files:
- `templates/index.html` - Upload page styles
- `templates/viewer.html` - Viewer page styles  
- `templates/editor.html` - Editor page styles

### Adding New Features
1. Modify `app.py` for new routes
2. Update templates for UI changes
3. Enhance `pdf_to_webpage.py` for conversion improvements

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests. 