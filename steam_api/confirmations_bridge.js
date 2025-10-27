const SteamCommunity = require('steamcommunity');
const SteamTotp = require('steam-totp');
const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3738;

const sessions = new Map();

app.post('/api/login-mafile', async (req, res) => {
    try {
        const { maFileData, sessionId } = req.body;
        
        if (!maFileData) {
            return res.status(400).json({ error: 'maFile data required' });
        }

        const community = new SteamCommunity();
        
        const authCode = SteamTotp.generateAuthCode(maFileData.shared_secret);
        
        const logOnOptions = {
            accountName: maFileData.account_name,
            password: req.body.password,
            twoFactorCode: authCode
        };

        community.login(logOnOptions, (err, sessionID, cookies, steamguard, oAuthToken) => {
            if (err) {
                console.error('Login error:', err);
                return res.status(401).json({ error: err.message });
            }

            const sid = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            sessions.set(sid, {
                community: community,
                cookies: cookies,
                steamID: community.steamID ? community.steamID.getSteamID64() : null,
                identitySecret: maFileData.identity_secret,
                deviceId: maFileData.device_id,
                sharedSecret: maFileData.shared_secret,
                loggedIn: true,
                createdAt: Date.now()
            });

            res.json({
                success: true,
                sessionId: sid,
                steamID: community.steamID ? community.steamID.getSteamID64() : null,
                accountName: maFileData.account_name
            });
        });

    } catch (error) {
        console.error('Login exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/login-with-secrets', async (req, res) => {
    try {
        const { username, password, sharedSecret, identitySecret, deviceId, sessionId } = req.body;
        
        if (!username || !password || !sharedSecret || !identitySecret) {
            return res.status(400).json({ 
                error: 'Username, password, sharedSecret and identitySecret required' 
            });
        }

        const community = new SteamCommunity();
        const authCode = SteamTotp.generateAuthCode(sharedSecret);

        community.login({
            accountName: username,
            password: password,
            twoFactorCode: authCode
        }, (err, sessionID, cookies, steamguard, oAuthToken) => {
            if (err) {
                return res.status(401).json({ error: err.message });
            }

            const sid = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            sessions.set(sid, {
                community: community,
                cookies: cookies,
                steamID: community.steamID.getSteamID64(),
                identitySecret: identitySecret,
                deviceId: deviceId || generateDeviceId(),
                sharedSecret: sharedSecret,
                loggedIn: true,
                createdAt: Date.now()
            });

            res.json({
                success: true,
                sessionId: sid,
                steamID: community.steamID.getSteamID64()
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/confirmations', async (req, res) => {
    try {
        const { sessionId } = req.query;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const key = SteamTotp.getConfirmationKey(
            session.identitySecret,
            time,
            'conf'
        );

        session.community.getConfirmations(time, key, (err, confirmations) => {
            if (err) {
                console.error('Get confirmations error:', err);
                return res.status(400).json({ error: err.message });
            }

            const formattedConfirmations = confirmations.map(conf => ({
                id: conf.id,
                type: conf.type,
                typeText: getConfirmationType(conf.type),
                creator: conf.creator,
                key: conf.key,
                title: conf.title || '',
                receiving: conf.receiving || '',
                time: conf.time,
                icon: conf.icon || '',
                offerID: conf.offerID || null,
                data: conf
            }));

            res.json({
                success: true,
                confirmations: formattedConfirmations,
                count: formattedConfirmations.length
            });
        });

    } catch (error) {
        console.error('Get confirmations exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/:confirmationId/accept', async (req, res) => {
    try {
        const { sessionId } = req.body;
        const { confirmationId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const confKey = SteamTotp.getConfirmationKey(session.identitySecret, time, 'conf');
        
        session.community.getConfirmations(time, confKey, (err, confirmations) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            const confirmation = confirmations.find(c => c.id === confirmationId);
            
            if (!confirmation) {
                return res.status(404).json({ error: 'Confirmation not found' });
            }

            const acceptTime = Math.floor(Date.now() / 1000);
            const acceptKey = SteamTotp.getConfirmationKey(
                session.identitySecret,
                acceptTime,
                'allow'
            );

            session.community.acceptConfirmation(
                confirmationId,
                confirmation.key,
                acceptTime,
                acceptKey,
                (err) => {
                    if (err) {
                        return res.status(400).json({ error: err.message });
                    }

                    res.json({
                        success: true,
                        confirmationId: confirmationId,
                        action: 'accepted'
                    });
                }
            );
        });

    } catch (error) {
        console.error('Accept confirmation exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/:confirmationId/cancel', async (req, res) => {
    try {
        const { sessionId } = req.body;
        const { confirmationId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const confKey = SteamTotp.getConfirmationKey(session.identitySecret, time, 'conf');
        
        session.community.getConfirmations(time, confKey, (err, confirmations) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            const confirmation = confirmations.find(c => c.id === confirmationId);
            
            if (!confirmation) {
                return res.status(404).json({ error: 'Confirmation not found' });
            }

            const cancelTime = Math.floor(Date.now() / 1000);
            const cancelKey = SteamTotp.getConfirmationKey(
                session.identitySecret,
                cancelTime,
                'cancel'
            );

            session.community.cancelConfirmation(
                confirmationId,
                confirmation.key,
                cancelTime,
                cancelKey,
                (err) => {
                    if (err) {
                        return res.status(400).json({ error: err.message });
                    }

                    res.json({
                        success: true,
                        confirmationId: confirmationId,
                        action: 'cancelled'
                    });
                }
            );
        });

    } catch (error) {
        console.error('Cancel confirmation exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/accept-all', async (req, res) => {
    try {
        const { sessionId } = req.body;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const confKey = SteamTotp.getConfirmationKey(session.identitySecret, time, 'conf');
        
        session.community.getConfirmations(time, confKey, (err, confirmations) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            if (confirmations.length === 0) {
                return res.json({
                    success: true,
                    accepted: 0,
                    message: 'No confirmations to accept'
                });
            }

            const acceptTime = Math.floor(Date.now() / 1000);
            const acceptKey = SteamTotp.getConfirmationKey(
                session.identitySecret,
                acceptTime,
                'allow'
            );

            session.community.acceptAllConfirmations(acceptTime, acceptKey, (err) => {
                if (err) {
                    return res.status(400).json({ error: err.message });
                }

                res.json({
                    success: true,
                    accepted: confirmations.length,
                    confirmations: confirmations.map(c => c.id)
                });
            });
        });

    } catch (error) {
        console.error('Accept all confirmations exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/cancel-all', async (req, res) => {
    try {
        const { sessionId } = req.body;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const confKey = SteamTotp.getConfirmationKey(session.identitySecret, time, 'conf');
        
        session.community.getConfirmations(time, confKey, async (err, confirmations) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            if (confirmations.length === 0) {
                return res.json({
                    success: true,
                    cancelled: 0,
                    message: 'No confirmations to cancel'
                });
            }

            let cancelledCount = 0;
            let errors = [];

            for (const confirmation of confirmations) {
                const cancelTime = Math.floor(Date.now() / 1000);
                const cancelKey = SteamTotp.getConfirmationKey(
                    session.identitySecret,
                    cancelTime,
                    'cancel'
                );

                await new Promise((resolve) => {
                    session.community.cancelConfirmation(
                        confirmation.id,
                        confirmation.key,
                        cancelTime,
                        cancelKey,
                        (err) => {
                            if (err) {
                                errors.push({ id: confirmation.id, error: err.message });
                            } else {
                                cancelledCount++;
                            }
                            resolve();
                        }
                    );
                });
            }

            res.json({
                success: true,
                cancelled: cancelledCount,
                errors: errors
            });
        });

    } catch (error) {
        console.error('Cancel all confirmations exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/confirmations/:confirmationId/details', async (req, res) => {
    try {
        const { sessionId } = req.query;
        const { confirmationId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const time = Math.floor(Date.now() / 1000);
        
        const confKey = SteamTotp.getConfirmationKey(session.identitySecret, time, 'details');
        
        session.community.getConfirmationOfferID(confirmationId, time, confKey, (err, offerID) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            res.json({
                success: true,
                confirmationId: confirmationId,
                offerID: offerID
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/logout', (req, res) => {
    try {
        const { sessionId } = req.body;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        sessions.delete(sessionId);
        res.json({ success: true });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        activeSessions: sessions.size,
        uptime: process.uptime(),
        service: 'confirmations'
    });
});

function getConfirmationType(type) {
    const types = {
        1: 'Generic',
        2: 'Trade',
        3: 'Market',
        4: 'FeatureOptOut',
        5: 'PhoneNumberChange',
        6: 'AccountRecovery'
    };
    return types[type] || 'Unknown';
}

function generateDeviceId() {
    const chars = '0123456789abcdef';
    let id = 'android:';
    for (let i = 0; i < 8; i++) id += chars[Math.floor(Math.random() * 16)];
    id += '-';
    for (let i = 0; i < 4; i++) id += chars[Math.floor(Math.random() * 16)];
    id += '-';
    for (let i = 0; i < 4; i++) id += chars[Math.floor(Math.random() * 16)];
    id += '-';
    for (let i = 0; i < 4; i++) id += chars[Math.floor(Math.random() * 16)];
    id += '-';
    for (let i = 0; i < 12; i++) id += chars[Math.floor(Math.random() * 16)];
    return id;
}

setInterval(() => {
    const now = Date.now();
    const MAX_SESSION_AGE = 12 * 60 * 60 * 1000;

    for (const [sid, session] of sessions.entries()) {
        if (now - session.createdAt > MAX_SESSION_AGE) {
            sessions.delete(sid);
            console.log(`Session ${sid} expired and removed`);
        }
    }
}, 30 * 60 * 1000);

app.listen(PORT, () => {
    console.log(`Steam Confirmations Bridge Server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/api/health`);
});
