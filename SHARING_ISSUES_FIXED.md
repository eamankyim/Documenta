# Document Sharing Issues - Analysis and Fixes

## Issues Found

### 1. Critical Bug: Shared Documents Could Not Be Viewed
**Location**: `templates/viewer.html` lines 580-585
**Problem**: When a document was accessed with `?share=1` parameter, the code immediately redirected to `/projects`, making it impossible to view shared documents.

**Code that caused the issue**:
```javascript
if (isShared) {
    try { sessionStorage.setItem('readonlyMode', '1'); } catch (_) {}
    try { window.location.replace('/projects'); } catch (_) { window.location.href = '/projects'; }
}
```

**Fix Applied**: Removed the problematic redirect and kept only the readonly mode setting.

### 2. Missing Share API Endpoint
**Problem**: The frontend tried to call `/api/share/${uniqueId}` but this endpoint didn't exist in the backend.

**Fix Applied**: Added a new `/api/share/<unique_id>` route in `app.py` that:
- Validates the project exists
- Verifies tokens when provided
- Accepts email addresses for sharing
- Generates share links with proper tokens
- Returns share links for each recipient

### 3. Incomplete View Route
**Location**: `app.py` route `/view/<unique_id>`
**Problem**: The view route didn't handle shared documents properly and lacked access control.

**Fix Applied**: Enhanced the view route to:
- Detect shared document access via `?share=1` parameter
- Verify share tokens for shared views
- Check database first, then fallback to file system
- Recreate missing files from database content
- Provide proper error handling

### 4. Missing Shared Documents API
**Problem**: No way to retrieve a list of documents that could be shared.

**Fix Applied**: Added `/api/shared_documents` endpoint that:
- Lists all projects with available tokens
- Provides share links for each document
- Handles errors gracefully

## Technical Details

### Share Token System
- Each project gets a unique token when first accessed
- Tokens are stored in the `tokens` table
- Share links include the token for verification
- Format: `/view/{unique_id}?share=1&token={token}`

### Access Control
- **Direct Access**: Users can view their own documents normally
- **Shared Access**: Requires valid share token and `?share=1` parameter
- **Read-only Mode**: Shared documents are automatically set to read-only

### Database Integration
- Projects are stored in the `projects` table
- Content is stored as HTML in the `content` field
- Files are recreated from database when missing
- Supports both file-based and database-based storage

## How to Test

### 1. Start the Application
```bash
python app.py
```

### 2. Test Basic Functionality
```bash
python test_sharing.py
```

### 3. Manual Testing Steps
1. Create a document or upload a PDF
2. Open the document in the viewer
3. Click the share button (three dots menu → Share)
4. Enter recipient emails
5. Send the share
6. Test the shared link with `?share=1` parameter

### 4. Expected Behavior
- Shared documents should load properly without redirecting
- Share modal should work and generate share links
- Share links should include proper tokens
- Shared documents should be read-only
- All sharing API endpoints should respond correctly

## Files Modified

1. **`templates/viewer.html`**
   - Fixed the critical redirect bug
   - Maintained readonly mode for shared documents

2. **`app.py`**
   - Added `/api/share/<unique_id>` route
   - Enhanced `/view/<unique_id>` route
   - Added `/api/shared_documents` route
   - Improved error handling and file recreation

3. **`test_sharing.py`** (new file)
   - Test script to verify sharing functionality

## Security Considerations

- Share tokens are required for shared document access
- Tokens are verified on the server side
- Shared documents are automatically set to read-only
- No authentication bypass for shared documents
- Proper error handling prevents information leakage

## Future Improvements

1. **Email Integration**: Send actual emails when sharing documents
2. **User-specific Sharing**: Track who shared what with whom
3. **Expiring Links**: Add expiration dates to share links
4. **Permission Levels**: Different access levels (view, comment, edit)
5. **Audit Logging**: Track document access and sharing history

## Conclusion

The main issue was a critical bug in the frontend JavaScript that prevented shared documents from being viewed. This has been fixed along with several missing backend components. The document sharing system should now work properly, allowing users to:

- Share documents via email
- Generate secure share links
- View shared documents without redirects
- Maintain proper access control
- Handle missing files gracefully
