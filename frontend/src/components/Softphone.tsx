import { useState, useEffect, useRef } from 'react';
import { Web } from 'sip.js';
import { Phone, PhoneOff, Mic, MicOff } from 'lucide-react';

export default function Softphone() {
  const [userAgent, setUserAgent] = useState<Web.SimpleUser | null>(null);
  const [status, setStatus] = useState<string>('disconnected');
  const [incomingNumber, setIncomingNumber] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const remoteAudioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    // Standard config, can be fetched from backend or local storage
    const serverUrl = 'wss://media.dishhome.ai:7443';
    const sipUri = 'sip:agent001@media.dishhome.ai';
    const password = 'agent_password_123'; // Replace with real auth

    if (!remoteAudioRef.current) return;

    const su = new Web.SimpleUser(serverUrl, {
      aor: sipUri,
      media: {
        constraints: { audio: true, video: false },
        remote: { audio: remoteAudioRef.current }
      }
    });

    su.delegate = {
      onCallReceived: async () => {
        setStatus('ringing');
        // Fetch customer data could happen here or via WebSocket event from backend
        // Use any to bypass private access for demonstration
        const session: any = (su as any).session;
        setIncomingNumber(session?.remoteIdentity?.uri?.user || 'Unknown Caller');
      },
      onCallAnswered: () => setStatus('connected'),
      onCallHangup: () => {
        setStatus('registered');
        setIncomingNumber(null);
      },
      onRegistered: () => setStatus('registered'),
      onUnregistered: () => setStatus('disconnected'),
    };

    // Try to connect and register
    su.connect()
      .then(() => su.register({
        requestOptions: {
          extraHeaders: [`Authorization: Digest username="agent001", realm="media.dishhome.ai", password="${password}"`]
        }
      }))
      .catch((err) => {
        console.error("Failed to connect SIP:", err);
        setStatus('error');
      });

    setUserAgent(su);

    return () => {
      su.unregister().then(() => su.disconnect());
    };
  }, []);

  const handleAnswer = () => {
    if (userAgent && status === 'ringing') {
      userAgent.answer();
    }
  };

  const handleHangup = () => {
    if (userAgent && (status === 'connected' || status === 'ringing')) {
      userAgent.hangup();
    }
  };

  const toggleMute = () => {
    if (userAgent && status === 'connected') {
      if (isMuted) {
        userAgent.unmute();
      } else {
        userAgent.mute();
      }
      setIsMuted(!isMuted);
    }
  };

  if (status === 'disconnected' || status === 'error') {
    return (
      <div className="fixed bottom-4 right-4 bg-slate-800 text-slate-400 px-4 py-2 rounded-lg shadow-lg text-sm flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-red-500"></span>
        Softphone Offline
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-72 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col z-50">
      <div className="bg-slate-900 text-white p-3 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${status === 'registered' ? 'bg-green-500' : 'bg-blue-500 animate-pulse'}`}></span>
          <span className="text-sm font-medium">Agent WebRTC</span>
        </div>
        <span className="text-xs text-slate-400 capitalize">{status}</span>
      </div>
      
      <div className="p-4 flex flex-col gap-4">
        {status === 'ringing' && (
          <div className="text-center animate-pulse text-dishhome-blue font-semibold">
            Incoming Call: {incomingNumber}
          </div>
        )}
        
        {status === 'connected' && (
          <div className="text-center text-green-600 font-semibold">
            Call Active: {incomingNumber}
          </div>
        )}

        <div className="flex justify-center gap-4">
          <button 
            onClick={handleAnswer}
            disabled={status !== 'ringing'}
            className="p-3 bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:bg-slate-200 text-white rounded-full transition-colors"
          >
            <Phone size={20} />
          </button>
          
          <button 
            onClick={toggleMute}
            disabled={status !== 'connected'}
            className={`p-3 rounded-full transition-colors text-white ${isMuted ? 'bg-orange-500' : 'bg-slate-700 hover:bg-slate-800'} disabled:opacity-50 disabled:bg-slate-200`}
          >
            {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
          
          <button 
            onClick={handleHangup}
            disabled={status !== 'connected' && status !== 'ringing'}
            className="p-3 bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:bg-slate-200 text-white rounded-full transition-colors"
          >
            <PhoneOff size={20} />
          </button>
        </div>
      </div>
      
      <audio ref={remoteAudioRef} autoPlay />
    </div>
  );
}
