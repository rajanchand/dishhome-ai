import { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Pause, Play, UserPlus } from 'lucide-react';
import { Web } from 'sip.js';
import { api, ApiError } from '../lib/api';

type Status =
  | 'Disconnected'
  | 'Connecting'
  | 'Registered'
  | 'In Call'
  | 'Ringing'
  | 'Error';

interface SipCredentials {
  ws_server: string;
  sip_uri: string;
  password: string;
  display_name: string;
}

export function Softphone() {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<Status>('Disconnected');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [number, setNumber] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isOnHold, setIsOnHold] = useState(false);

  const simpleUserRef = useRef<Web.SimpleUser | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const sipDomainRef = useRef<string>('');

  useEffect(() => {
    if (!isOpen || status !== 'Disconnected') return;

    let cancelled = false;
    setStatus('Connecting');
    setErrorMsg(null);

    const initSIP = async () => {
      if (!remoteAudioRef.current) return;

      let creds: SipCredentials;
      try {
        creds = await api.get<SipCredentials>('/telephony/sip-credentials');
      } catch (e) {
        if (cancelled) return;
        const msg =
          e instanceof ApiError
            ? e.status === 503
              ? 'Softphone not provisioned — contact your administrator.'
              : `Failed to fetch SIP credentials: ${e.message}`
            : 'Failed to fetch SIP credentials.';
        setErrorMsg(msg);
        setStatus('Error');
        return;
      }

      const options: Web.SimpleUserOptions = {
        aor: creds.sip_uri,
        media: { remote: { audio: remoteAudioRef.current! } },
        userAgentOptions: {
          authorizationPassword: creds.password,
          displayName: creds.display_name,
        },
      };

      // Extract the SIP domain from the AOR (sip:user@domain) so dialed
      // numbers route to the same realm we registered against.
      sipDomainRef.current = creds.sip_uri.split('@')[1] ?? '';

      const simpleUser = new Web.SimpleUser(creds.ws_server, options);

      simpleUser.delegate = {
        onCallCreated: () => setStatus('Ringing'),
        onCallAnswered: () => setStatus('In Call'),
        onCallHangup: () => {
          setStatus('Registered');
          setIsMuted(false);
          setIsOnHold(false);
        },
        onRegistered: () => setStatus('Registered'),
        onUnregistered: () => setStatus('Disconnected'),
      };

      try {
        await simpleUser.connect();
        await simpleUser.register();
        if (cancelled) {
          await simpleUser.disconnect();
          return;
        }
        simpleUserRef.current = simpleUser;
      } catch (error) {
        console.error('SIP connection failed', error);
        if (cancelled) return;
        // Surface the failure honestly. Earlier code pretended to be
        // "Registered" after a setTimeout, which made the UI lie about a
        // broken phone.
        setErrorMsg(
          error instanceof Error ? error.message : 'SIP connection failed.',
        );
        setStatus('Error');
      }
    };

    initSIP();

    return () => {
      cancelled = true;
      const user = simpleUserRef.current;
      simpleUserRef.current = null;
      if (user) {
        user
          .unregister()
          .catch(() => {})
          .finally(() => user.disconnect().catch(() => {}));
      }
    };
  }, [isOpen]);

  const callable = status === 'Registered' && !!simpleUserRef.current;

  const handleDial = (digit: string) => {
    setNumber((prev) => prev + digit);
  };

  const handleCall = async () => {
    if (!number || !callable) return;
    setStatus('Ringing');
    try {
      // Dial within the SIP domain we registered against — never hardcode.
      const domain = sipDomainRef.current;
      if (!domain) {
        throw new Error('SIP domain unknown — re-open the softphone.');
      }
      await simpleUserRef.current!.call(`sip:${number}@${domain}`);
    } catch (e) {
      console.error(e);
      setStatus('Registered');
      setErrorMsg(e instanceof Error ? e.message : 'Call failed.');
    }
  };

  const handleHangup = async () => {
    if (!simpleUserRef.current) return;
    try {
      await simpleUserRef.current.hangup();
    } catch (e) {
      console.error(e);
    } finally {
      setNumber('');
      setIsMuted(false);
      setIsOnHold(false);
    }
  };

  const toggleMute = () => {
    if (!simpleUserRef.current) return;
    if (isMuted) simpleUserRef.current.unmute();
    else simpleUserRef.current.mute();
    setIsMuted(!isMuted);
  };

  const toggleHold = async () => {
    if (!simpleUserRef.current) return;
    try {
      if (isOnHold) await simpleUserRef.current.unhold();
      else await simpleUserRef.current.hold();
      setIsOnHold(!isOnHold);
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-dishhome-orange hover:bg-orange-600 text-white p-4 rounded-full shadow-lg transition-transform hover:scale-105 z-50 flex items-center justify-center"
        aria-label="Open softphone"
      >
        <Phone size={24} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-80 bg-white border border-gray-200 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
      <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-sm">DishHome Softphone</h3>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`w-2 h-2 rounded-full ${
                status === 'Registered'
                  ? 'bg-green-500'
                  : status === 'In Call'
                  ? 'bg-red-500'
                  : status === 'Connecting'
                  ? 'bg-yellow-500'
                  : status === 'Error'
                  ? 'bg-red-400'
                  : 'bg-gray-500'
              }`}
            />
            <span className="text-xs text-gray-300">{status}</span>
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label="Close softphone"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {errorMsg && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-xs text-red-700">
          {errorMsg}
        </div>
      )}

      <div className="p-6 pb-2 text-center">
        <input
          type="text"
          value={number}
          onChange={(e) => setNumber(e.target.value)}
          placeholder="Enter number..."
          className="w-full text-center text-2xl font-light outline-none bg-transparent mb-2 placeholder-gray-300"
          readOnly={status === 'In Call' || status === 'Ringing'}
        />
        {status === 'In Call' && (
          <div className="text-sm text-gray-500 animate-pulse">Live Call</div>
        )}
      </div>

      {status !== 'In Call' && status !== 'Ringing' && (
        <div className="px-6 pb-4">
          <div className="grid grid-cols-3 gap-3">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, '*', 0, '#'].map((digit) => (
              <button
                key={digit}
                onClick={() => handleDial(digit.toString())}
                className="h-12 rounded-lg bg-gray-50 hover:bg-gray-100 text-lg font-medium text-gray-700 transition-colors"
              >
                {digit}
              </button>
            ))}
          </div>
        </div>
      )}

      {(status === 'In Call' || status === 'Ringing') && (
        <div className="px-6 py-4 flex-1 flex flex-col justify-center gap-6 bg-gray-50">
          <div className="grid grid-cols-3 gap-4">
            <button
              onClick={toggleMute}
              className={`flex flex-col items-center gap-1 ${isMuted ? 'text-red-500' : 'text-gray-600'}`}
            >
              <div className={`p-3 rounded-full ${isMuted ? 'bg-red-100' : 'bg-white shadow-sm'}`}>
                {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
              </div>
              <span className="text-xs font-medium">Mute</span>
            </button>

            <button
              onClick={toggleHold}
              className={`flex flex-col items-center gap-1 ${isOnHold ? 'text-dishhome-orange' : 'text-gray-600'}`}
            >
              <div className={`p-3 rounded-full ${isOnHold ? 'bg-orange-100' : 'bg-white shadow-sm'}`}>
                {isOnHold ? <Play size={20} /> : <Pause size={20} />}
              </div>
              <span className="text-xs font-medium">Hold</span>
            </button>

            <button className="flex flex-col items-center gap-1 text-gray-600" disabled>
              <div className="p-3 rounded-full bg-white shadow-sm">
                <UserPlus size={20} />
              </div>
              <span className="text-xs font-medium">Transfer</span>
            </button>
          </div>
        </div>
      )}

      <div className="p-6 pt-2 flex justify-center">
        {status === 'In Call' || status === 'Ringing' ? (
          <button
            onClick={handleHangup}
            className="w-16 h-16 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center shadow-md transition-transform hover:scale-105"
            aria-label="Hang up"
          >
            <PhoneOff size={24} />
          </button>
        ) : (
          <button
            onClick={handleCall}
            disabled={!number || !callable}
            className={`w-16 h-16 rounded-full flex items-center justify-center shadow-md transition-transform ${
              number && callable
                ? 'bg-green-500 hover:bg-green-600 text-white hover:scale-105'
                : 'bg-green-300 text-white cursor-not-allowed'
            }`}
            aria-label="Call"
          >
            <Phone size={24} />
          </button>
        )}
      </div>

      <audio ref={remoteAudioRef} autoPlay />
    </div>
  );
}
