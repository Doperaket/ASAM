const SteamCommunity = require('steamcommunity');
const TradeOfferManager = require('steam-tradeoffer-manager');
const SteamTotp = require('steam-totp');
const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3737;

const sessions = new Map();

app.post('/api/login', async (req, res) => {
    try {
        const { username, password, sharedSecret, sessionId } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ error: 'Username and password required' });
        }

        const community = new SteamCommunity();
        const manager = new TradeOfferManager({
            community: community,
            language: 'ru',
            pollInterval: 10000
        });

        const logOnOptions = {
            accountName: username,
            password: password
        };

        if (sharedSecret) {
            logOnOptions.twoFactorCode = SteamTotp.generateAuthCode(sharedSecret);
        }

        community.login(logOnOptions, (err, sessionID, cookies, steamguard, oAuthToken) => {
            if (err) {
                console.error('Login error:', err);
                return res.status(401).json({ 
                    error: err.message,
                    requires2FA: err.message.includes('SteamGuard')
                });
            }

            const sid = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            sessions.set(sid, {
                community: community,
                manager: manager,
                cookies: cookies,
                steamID: community.steamID ? community.steamID.getSteamID64() : null,
                loggedIn: true,
                createdAt: Date.now()
            });

            manager.setCookies(cookies);

            res.json({
                success: true,
                sessionId: sid,
                steamID: community.steamID ? community.steamID.getSteamID64() : null
            });
        });

    } catch (error) {
        console.error('Login exception:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/login-2fa', async (req, res) => {
    try {
        const { username, password, twoFactorCode, sessionId } = req.body;
        
        if (!username || !password || !twoFactorCode) {
            return res.status(400).json({ error: 'Username, password and 2FA code required' });
        }

        const community = new SteamCommunity();
        const manager = new TradeOfferManager({
            community: community,
            language: 'ru'
        });

        community.login({
            accountName: username,
            password: password,
            twoFactorCode: twoFactorCode
        }, (err, sessionID, cookies, steamguard, oAuthToken) => {
            if (err) {
                return res.status(401).json({ error: err.message });
            }

            const sid = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            sessions.set(sid, {
                community: community,
                manager: manager,
                cookies: cookies,
                steamID: community.steamID.getSteamID64(),
                loggedIn: true,
                createdAt: Date.now()
            });

            manager.setCookies(cookies);

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

app.post('/api/acknowledge-trade-protection', async (req, res) => {
    try {
        const { sessionId } = req.body;
        
        if (!sessionId) {
            return res.status(400).json({ error: 'Session ID required' });
        }

        const sessionData = sessions.get(sessionId);
        if (!sessionData) {
            return res.status(404).json({ error: 'Session not found' });
        }

        const { community } = sessionData;
        
        community.acknowledgeTradeProtection((err) => {
            if (err) {
                console.error(`[${sessionId}] Trade protection acknowledgment failed:`, err);
                return res.status(500).json({ 
                    error: 'Failed to acknowledge trade protection', 
                    details: err.message 
                });
            }
            
            res.json({ 
                success: true, 
                message: 'Trade protection acknowledged successfully'
            });
        });
        
    } catch (error) {
        console.error('Acknowledge trade protection error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/create', async (req, res) => {
    try {
        const { sessionId, partnerSteamId, partnerTradeUrl, itemsFromMe, itemsFromThem, message, token } = req.body;
        
        console.log(`[DEBUG] Trade creation request:`, {
            sessionId: sessionId ? 'present' : 'missing',
            partnerSteamId,
            partnerTradeUrl,
            itemsFromMe: itemsFromMe ? itemsFromMe.length : 0,
            itemsFromThem: itemsFromThem ? itemsFromThem.length : 0,
            message,
            token
        });
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        
        let offer;
        let accessToken = token;
        
        if (partnerTradeUrl) {
            console.log(`[DEBUG] Parsing trade URL: ${partnerTradeUrl}`);
            try {
                const url = new URL(partnerTradeUrl);
                console.log(`[DEBUG] URL parsed successfully`);
                const partnerId = url.searchParams.get('partner');
                accessToken = url.searchParams.get('token');
                
                console.log(`[DEBUG] Partner ID: ${partnerId}, Token: ${accessToken}`);
                
                if (!partnerId) {
                    console.error(`[ERROR] Missing partner parameter in URL: ${partnerTradeUrl}`);
                    return res.status(400).json({ error: 'Invalid trade URL: missing partner parameter' });
                }
                
                const steamId64 = (BigInt(partnerId) + BigInt('76561197960265728')).toString();
                console.log(`[DEBUG] Converted Partner ID ${partnerId} to Steam ID64: ${steamId64}`);
                
                console.log(`[DEBUG] Creating offer with steamId64: ${steamId64}, token: ${accessToken}`);
                offer = session.manager.createOffer(steamId64, accessToken);
            } catch (urlError) {
                console.error(`[ERROR] URL parsing failed: ${urlError.message}`);
                return res.status(400).json({ error: `Invalid trade URL format: ${urlError.message}` });
            }
        } else if (partnerSteamId) {
            offer = session.manager.createOffer(partnerSteamId);
        } else {
            return res.status(400).json({ error: 'Either partnerTradeUrl or partnerSteamId must be provided' });
        }

        if (itemsFromMe && itemsFromMe.length > 0) {
            offer.addMyItems(itemsFromMe);
        }

        if (itemsFromThem && itemsFromThem.length > 0) {
            offer.addTheirItems(itemsFromThem);
        }

        if (message) {
            offer.setMessage(message);
        }

        offer.send((err, status) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            res.json({
                success: true,
                offerId: offer.id,
                status: status
            });
        }, token);

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/trade/:offerId', async (req, res) => {
    try {
        const { sessionId } = req.query;
        const { offerId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOffer(offerId, (err, offer) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            res.json({
                success: true,
                offer: {
                    id: offer.id,
                    state: offer.state,
                    message: offer.message,
                    itemsToGive: offer.itemsToGive,
                    itemsToReceive: offer.itemsToReceive,
                    created: offer.created,
                    updated: offer.updated,
                    expires: offer.expires
                }
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/:offerId/accept', async (req, res) => {
    try {
        const { sessionId } = req.body;
        const { offerId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOffer(offerId, (err, offer) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            offer.accept((err, status) => {
                if (err) {
                    return res.status(400).json({ error: err.message });
                }

                res.json({
                    success: true,
                    status: status
                });
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/:offerId/decline', async (req, res) => {
    try {
        const { sessionId } = req.body;
        const { offerId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOffer(offerId, (err, offer) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            offer.decline((err) => {
                if (err) {
                    return res.status(400).json({ error: err.message });
                }

                res.json({ success: true });
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/:offerId/cancel', async (req, res) => {
    try {
        const { sessionId } = req.body;
        const { offerId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOffer(offerId, (err, offer) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            offer.cancel((err) => {
                if (err) {
                    return res.status(400).json({ error: err.message });
                }

                res.json({ success: true });
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/trade/offers', async (req, res) => {
    try {
        const { sessionId, filter } = req.query;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const filterType = filter || 'active'; // active, historical, all

        session.manager.getOffers(filterType === 'active' ? 1 : 2, (err, sent, received) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            res.json({
                success: true,
                sent: sent.map(o => ({
                    id: o.id,
                    state: o.state,
                    message: o.message,
                    created: o.created,
                    updated: o.updated
                })),
                received: received.map(o => ({
                    id: o.id,
                    state: o.state,
                    message: o.message,
                    created: o.created,
                    updated: o.updated
                }))
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/inventory/:steamId/:appId/:contextId', async (req, res) => {
    try {
        const { sessionId } = req.query;
        const { steamId, appId, contextId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.community.getUserInventoryContents(
            steamId,
            parseInt(appId),
            parseInt(contextId),
            true,
            (err, inventory, currencies) => {
                if (err) {
                    return res.status(400).json({ error: err.message });
                }

                res.json({
                    success: true,
                    items: inventory.map(item => ({
                        assetid: item.assetid,
                        classid: item.classid,
                        instanceid: item.instanceid,
                        amount: item.amount,
                        name: item.name,
                        market_name: item.market_name,
                        market_hash_name: item.market_hash_name,
                        type: item.type,
                        tradable: item.tradable,
                        marketable: item.marketable,
                        icon_url: item.icon_url
                    })),
                    currencies: currencies
                });
            }
        );

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

        const session = sessions.get(sessionId);
        
        if (session.manager) {
            session.manager.shutdown();
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
        uptime: process.uptime()
    });
});

app.get('/api/wallet/:sessionId', async (req, res) => {
    try {
        const { sessionId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        const community = session.community;

        if (typeof community.httpRequest === 'function') {
            const options = {
                method: 'GET',
                uri: 'https://steamcommunity.com/market/',
                followRedirect: true,
                maxRedirects: 5
            };
            
            community.httpRequest(options, (err, response, body) => {
                if (err) {
                    console.error('Wallet request error:', err);
                    return res.status(500).json({ 
                        error: 'Failed to get wallet balance',
                        details: err.message 
                    });
                }
                
                console.log(`Wallet request completed. Status: ${response ? response.statusCode : 'unknown'}`);
                console.log(`Response body length: ${body ? body.length : 0}`);
                
                const walletPatterns = [
                    /wallet_balance":\s*"([^"]+)"/,
                    /wallet_currency":\s*(\d+)/,
                    /marketWalletBalanceText[^>]*>([^<]+)</i,
                    /"balance":"([^"]+)"/,
                    /Баланс\s+([^\s<]+)/i
                ];
                
                console.log('Searching for wallet patterns...');
                walletPatterns.forEach((pattern, index) => {
                    const match = body.match(pattern);
                    if (match) {
                        console.log(`Pattern ${index + 1} matched:`, match[1]);
                    }
                });
                
                try {
                    let balance = '0.00';
                    let currency = 'USD';
                    let formatted = '$0.00';
                    
                    const walletBalanceMatch = body.match(/wallet_balance":\s*"([^"]+)"/);
                    const walletCurrencyMatch = body.match(/wallet_currency":\s*(\d+)/);
                    
                    if (walletBalanceMatch) {
                        const rawBalance = walletBalanceMatch[1];
                        console.log(`Raw wallet balance found: ${rawBalance}`);
                        
                        if (walletCurrencyMatch) {
                            const currencyCode = parseInt(walletCurrencyMatch[1]);
                            console.log(`Currency code found: ${currencyCode}`);
                            
                            switch (currencyCode) {
                                case 1: currency = 'USD'; break;
                                case 3: currency = 'EUR'; break;
                                case 5: currency = 'RUB'; break;
                                case 18: currency = 'UAH'; break;
                                default: currency = 'USD';
                            }
                        }
                        
                        if (rawBalance && rawBalance !== '0') {
                            const numericBalance = parseInt(rawBalance);
                            console.log(`Numeric balance: ${numericBalance}, Currency: ${currency}`);
                            
                            if (!isNaN(numericBalance)) {
                                switch (currency) {
                                    case 'UAH':
                                        balance = (numericBalance / 100).toFixed(2);
                                        formatted = balance.replace('.', ',') + ' ₴';
                                        break;
                                    case 'RUB':
                                        balance = (numericBalance / 100).toFixed(2);
                                        formatted = balance.replace('.', ',') + ' руб.';
                                        break;
                                    case 'EUR':
                                        balance = (numericBalance / 100).toFixed(2);
                                        formatted = '€' + balance;
                                        break;
                                    case 'USD':
                                    default:
                                        balance = (numericBalance / 100).toFixed(2);
                                        formatted = '$' + balance;
                                        break;
                                }
                            }
                        } else {
                            balance = '0.00';
                            switch (currency) {
                                case 'UAH': formatted = '0,00 ₴'; break;
                                case 'RUB': formatted = '0,00 руб.'; break;
                                case 'EUR': formatted = '€0.00'; break;
                                default: formatted = '$0.00'; break;
                            }
                        }
                    }
                    
                    if (!walletBalanceMatch) {
                        console.log('Primary wallet balance not found, trying fallback patterns...');
                        
                        const fallbackPatterns = [
                            /market_buynow_dialog_balance_container[^>]*>([^<]+)</i,
                            /"marketWalletBalanceText":"([^"]+)"/,
                            /id="marketWalletBalanceAmount"[^>]*>([^<]+)</,
                            /wallet.*?(\d+[.,]\d+)/i
                        ];
                        
                        for (let i = 0; i < fallbackPatterns.length; i++) {
                            const match = body.match(fallbackPatterns[i]);
                            if (match) {
                                console.log(`Fallback pattern ${i + 1} found balance: ${match[1]}`);
                                formatted = match[1].trim();
                                
                                const numMatch = formatted.match(/([\d,]+[.,]?\d*)/);
                                if (numMatch) {
                                    balance = numMatch[1].replace(/,/g, '');
                                    
                                    if (formatted.includes('₴') || formatted.includes('грн')) {
                                        currency = 'UAH';
                                    } else if (formatted.includes('₽') || formatted.includes('руб')) {
                                        currency = 'RUB';
                                    } else if (formatted.includes('€')) {
                                        currency = 'EUR';
                                    } else if (formatted.includes('$')) {
                                        currency = 'USD';
                                    }
                                }
                                break;
                            }
                        }
                        
                        if (!formatted || formatted === '$0.00') {
                            console.log('No balance found, checking for error messages...');
                            const errorPatterns = [
                                /error[^>]*>([^<]+)</i,
                                /wallet.*error/i,
                                /login.*required/i
                            ];
                            
                            errorPatterns.forEach((pattern, index) => {
                                const match = body.match(pattern);
                                if (match) {
                                    console.log(`Error pattern ${index + 1} found:`, match[1] || match[0]);
                                }
                            });
                        }
                    }
                    
                    console.log(`Final result - Balance: ${balance}, Currency: ${currency}, Formatted: ${formatted}`);
                    
                    res.json({
                        success: true,
                        balance: parseFloat(balance) || 0,
                        currency: currency,
                        formatted: formatted
                    });
                    
                } catch (parseErr) {
                    console.error('Parse error:', parseErr);
                    res.status(500).json({ 
                        error: 'Failed to parse balance',
                        details: parseErr.message 
                    });
                }
            });
        } else {
            console.error('httpRequest method not available');
            res.status(500).json({ 
                error: 'HTTP request method not available'
            });
        }

    } catch (error) {
        console.error('Wallet API error:', error);
        res.status(500).json({ 
            error: 'Server error', 
            details: error.message 
        });
    }
});

app.get('/api/trade-url', async (req, res) => {
    try {
        const { sessionId } = req.query;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOfferToken((err, token) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            res.json({
                success: true,
                token: token,
                tradeUrl: `https://steamcommunity.com/tradeoffer/new/?partner=${session.steamID}&token=${token}`
            });
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/trade/incoming', async (req, res) => {
    try {
        const { sessionId } = req.query;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.manager.getOffers(1, (err, sent, received) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            const incomingOffers = received.filter(offer => 
                offer.state === 2 // ETradeOfferState.Active
            ).map(offer => ({
                id: offer.id,
                state: offer.state,
                partner: offer.partner.toString(),
                message: offer.message || '',
                itemsToGive: offer.itemsToGive.length,
                itemsToReceive: offer.itemsToReceive.length,
                created: offer.created,
                expires: offer.expires,
                tradeID: offer.tradeID
            }));

            res.json({
                success: true,
                offers: incomingOffers,
                count: incomingOffers.length
            });
        });

    } catch (error) {
        console.error('[ERROR] Getting incoming trades:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/auto-accept', async (req, res) => {
    try {
        const { sessionId, partnerSteamId, acceptAll = false } = req.body;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);
        let acceptedOffers = [];
        let errors = [];

        session.manager.getOffers(1, (err, sent, received) => {
            if (err) {
                return res.status(400).json({ error: err.message });
            }

            let offersToAccept = received.filter(offer => 
                offer.state === 2 // Active
            );

            if (partnerSteamId && !acceptAll) {
                offersToAccept = offersToAccept.filter(offer => 
                    offer.partner.toString() === partnerSteamId.toString()
                );
            }

            console.log(`[DEBUG] Auto-accepting ${offersToAccept.length} trade offers`);

            if (offersToAccept.length === 0) {
                return res.json({
                    success: true,
                    message: 'No offers to accept',
                    accepted: [],
                    errors: []
                });
            }

            let processedCount = 0;
            const totalOffers = offersToAccept.length;

            offersToAccept.forEach(offer => {
                console.log(`[DEBUG] Accepting offer ${offer.id} from ${offer.partner}`);
                
                offer.accept((acceptErr, status) => {
                    processedCount++;
                    
                    if (acceptErr) {
                        console.error(`[ERROR] Failed to accept offer ${offer.id}:`, acceptErr.message);
                        errors.push({
                            offerId: offer.id,
                            error: acceptErr.message
                        });
                    } else {
                        console.log(`[SUCCESS] Accepted offer ${offer.id}, status: ${status}`);
                        acceptedOffers.push({
                            offerId: offer.id,
                            partner: offer.partner.toString(),
                            status: status
                        });
                    }

                    if (processedCount === totalOffers) {
                        res.json({
                            success: true,
                            accepted: acceptedOffers,
                            errors: errors,
                            total: totalOffers
                        });
                    }
                });
            });
        });

    } catch (error) {
        console.error('[ERROR] Auto-accept error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/trade/accept-sent/:offerId', async (req, res) => {
    try {
        const { sessionId, receiverSessionId } = req.body;
        const { offerId } = req.params;
        
        console.log(`[DEBUG] Accept sent trade request: offerId=${offerId}, sessionId=${sessionId}, receiverSessionId=${receiverSessionId}`);
        
        const targetSessionId = receiverSessionId || sessionId;
        
        if (!targetSessionId || !sessions.has(targetSessionId)) {
            return res.status(401).json({ error: 'Invalid receiver session' });
        }

        const session = sessions.get(targetSessionId);

        session.manager.getOffer(offerId, (err, offer) => {
            if (err) {
                console.error(`[ERROR] Failed to get offer ${offerId}:`, err.message);
                return res.status(400).json({ error: err.message });
            }

            console.log(`[DEBUG] Offer ${offerId} found, state: ${offer.state}, partner: ${offer.partner}`);

            if (offer.state !== 2) {
                return res.status(400).json({ 
                    error: `Trade offer is not active (state: ${offer.state})` 
                });
            }

            offer.accept((acceptErr, status) => {
                if (acceptErr) {
                    console.error(`[ERROR] Failed to accept offer ${offerId}:`, acceptErr.message);
                    return res.status(400).json({ error: acceptErr.message });
                }

                console.log(`[SUCCESS] Accepted offer ${offerId}, status: ${status}`);
                res.json({
                    success: true,
                    offerId: offerId,
                    status: status
                });
            });
        });

    } catch (error) {
        console.error('[ERROR] Accept sent trade error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/confirmations/:sessionId', async (req, res) => {
    try {
        const { sessionId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.community.getConfirmations((err, confirmations) => {
            if (err) {
                console.error('[ERROR] Getting confirmations:', err);
                return res.status(400).json({ error: err.message });
            }

            const formattedConfirmations = confirmations.map(conf => ({
                id: conf.id,
                key: conf.key,
                type: conf.type,
                creator: conf.creator,
                title: conf.title || conf.headline,
                description: conf.summary || 'Нет описания',
                time: new Date(conf.time * 1000).toLocaleString('ru-RU'),
                icon: conf.icon
            }));

            res.json({
                success: true,
                confirmations: formattedConfirmations
            });
        });

    } catch (error) {
        console.error('[ERROR] Confirmations error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/:sessionId/:confirmationId', async (req, res) => {
    try {
        const { sessionId, confirmationId } = req.params;
        const { confirmationKey, accept = true } = req.body;
        
        console.log(`[DEBUG] Confirming: sessionId=${sessionId}, confirmationId=${confirmationId}, key=${confirmationKey}, accept=${accept}`);
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        if (!confirmationKey) {
            return res.status(400).json({ error: 'Confirmation key required' });
        }

        const session = sessions.get(sessionId);

        const action = accept ? 'accept' : 'cancel';
        
        session.community.respondToConfirmation(confirmationId, confirmationKey, accept, (err) => {
            if (err) {
                console.error(`[ERROR] Failed to ${action} confirmation ${confirmationId}:`, err.message);
                return res.status(400).json({ error: err.message });
            }

            console.log(`[SUCCESS] Confirmation ${confirmationId} ${action}ed successfully`);
            res.json({
                success: true,
                action: action,
                confirmationId: confirmationId
            });
        });

    } catch (error) {
        console.error('[ERROR] Confirmation action error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/confirmations/:sessionId/accept-all', async (req, res) => {
    try {
        const { sessionId } = req.params;
        
        if (!sessionId || !sessions.has(sessionId)) {
            return res.status(401).json({ error: 'Invalid session' });
        }

        const session = sessions.get(sessionId);

        session.community.getConfirmations((err, confirmations) => {
            if (err) {
                console.error('[ERROR] Getting confirmations for accept-all:', err);
                return res.status(400).json({ error: err.message });
            }

            if (!confirmations || confirmations.length === 0) {
                return res.json({
                    success: true,
                    message: 'No confirmations to accept',
                    accepted: 0
                });
            }

            let acceptedCount = 0;
            let errors = [];
            let processedCount = 0;
            const totalCount = confirmations.length;

            console.log(`[DEBUG] Accepting ${totalCount} confirmations`);

            confirmations.forEach(conf => {
                session.community.respondToConfirmation(conf.id, conf.key, true, (acceptErr) => {
                    processedCount++;
                    
                    if (acceptErr) {
                        console.error(`[ERROR] Failed to accept confirmation ${conf.id}:`, acceptErr.message);
                        errors.push({
                            confirmationId: conf.id,
                            error: acceptErr.message
                        });
                    } else {
                        console.log(`[SUCCESS] Accepted confirmation ${conf.id}`);
                        acceptedCount++;
                    }

                    if (processedCount === totalCount) {
                        res.json({
                            success: true,
                            accepted: acceptedCount,
                            errors: errors,
                            total: totalCount
                        });
                    }
                });
            });
        });

    } catch (error) {
        console.error('[ERROR] Accept all confirmations error:', error);
        res.status(500).json({ error: error.message });
    }
});

setInterval(() => {
    const now = Date.now();
    const MAX_SESSION_AGE = 12 * 60 * 60 * 1000; // 12 часов

    for (const [sid, session] of sessions.entries()) {
        if (now - session.createdAt > MAX_SESSION_AGE) {
            if (session.manager) {
                session.manager.shutdown();
            }
            sessions.delete(sid);
            console.log(`Session ${sid} expired and removed`);
        }
    }
}, 30 * 60 * 1000);

app.listen(PORT, () => {
    console.log(`Steam Bridge Server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/api/health`);
});
