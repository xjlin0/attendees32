function openBackupModal() {
    const msg = document.querySelector('.messagelist');
    if (msg) msg.style.display = 'none';  // Hide previous errors such as wrong password

    const modal = document.getElementById('backup-modal-overlay');
    modal.style.visibility = 'visible';
    modal.style.opacity = '1';
    modal.style.pointerEvents = 'auto';

    // Delay focus to give password manager some time to fill DOM
    setTimeout(function() {
        document.getElementById('backup-pwd-input').focus();
    }, 300);

    document.addEventListener('keydown', handleEscKey);  // User Esc to close modal
}

function closeBackupModal() {
    const modal = document.getElementById('backup-modal-overlay');
    modal.style.visibility = 'hidden';
    modal.style.opacity = '0';
    modal.style.pointerEvents = 'none';
    
    // 延遲清除密碼，避免阻斷正在送出的 POST Request
    setTimeout(function() {
        const pwdInput = document.getElementById('backup-pwd-input');
        if (pwdInput) pwdInput.value = '';
    }, 200);

    document.removeEventListener('keydown', handleEscKey);
}

function handleEscKey(e) {
    if (e.key === 'Escape' || e.keyCode === 27) {
        closeBackupModal();
    }
}
