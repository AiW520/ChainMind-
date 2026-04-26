export default function ChatMessage({ message, isUser }) {
    return (
        <div style={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            animation: 'fadeIn 0.3s ease'
        }}>
            {!isUser && (
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    marginRight: '10px',
                    flexShrink: 0
                }}>
                    🤖
                </div>
            )}
            
            <div style={{
                maxWidth: '70%',
                padding: '14px 18px',
                borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                background: isUser 
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                    : 'rgba(255, 255, 255, 0.08)',
                color: isUser ? '#fff' : 'rgba(255, 255, 255, 0.9)',
                fontSize: '14px',
                lineHeight: '1.5',
                boxShadow: isUser ? 'none' : '0 2px 8px rgba(0, 0, 0, 0.2)',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap'
            }}>
                {message}
            </div>
            
            {isUser && (
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    marginLeft: '10px',
                    flexShrink: 0
                }}>
                    👤
                </div>
            )}
            
            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
