import { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Pause, Play, UserPlus } from 'lucide-react';
import { Web } from 'sip.js';

interface SoftphoneProps {
  wsServer?: string;
  sipUri?: string;
  password?: string;
}

export function Softphone({ 
  wsServer = "wss://sip.dishhome.com:7443", 
  sipUri = "sip:agent@dishhome.com", 
  password = "password" 
}: SoftphoneProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<'Disconnected' | 'Connecting' | 'Registered' | 'In Call' | 'Ringing'>('Disconnected');
  const [number, setNumber] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isOnHold, setIsOnHold] = useState(false);
  
  // SIP.js references
  const simpleUserRef = useRef<Web.SimpleUser | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Only connect when opened
    if (!isOpen || status !== 'Disconnected') return;

    setStatus('Connecting');

    const initSIP = async () => {
      // Need the audio element mounted
      if (!remoteAudioRef.current) return;
      
      const server = wsServer;
      const options: Web.SimpleUserOptions = {
        aor: sipUri,
        media: {
          remote: {
            audio: remoteAudioRef.current,
          }
        },
        userAgentOptions: {
          authorizationPassword: password,
        }
      };

      const simpleUser = new Web.SimpleUser(server, options);
      
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
        simpleUserRef.current = simpleUser;
      } catch (error) {
        console.error("SIP connection failed", error);
        // Fallback for mock environment if no server is running
        setTimeout(() => setStatus('Registered'), 1000); 
      }
    };

    initSIP();

    return () => {
      if (simpleUserRef.current) {
        simpleUserRef.current.unregister();
        simpleUserRef.current.disconnect();
        simpleUserRef.current = null;
      }
    };
  }, [isOpen, wsServer, sipUri, password]);

  const handleDial = (digit: string) => {
    setNumber(prev => prev + digit);
  };

  const handleCall = async () => {
    if (!number) return;
    setStatus('Ringing');
    if (simpleUserRef.current && simpleUserRef.current.isConnected()) {
      try {
        await simpleUserRef.current.call(`sip:${number}@dishhome.com`);
      } catch (e) {
        console.error(e);
        setStatus('Registered');
      }
    } else {
      // Mock call for UI demo if SIP is disconnected
      setTimeout(() => setStatus('In Call'), 2000);
    }
  };

  const handleHangup = async () => {
    if (simpleUserRef.current && simpleUserRef.current.isConnected()) {
      await simpleUserRef.current.hangup();
    } else {
      // Mock hangup
      setStatus('Registered');
      setNumber('');
      setIsMuted(false);
      setIsOnHold(false);
    }
  };

  const toggleMute = () => {
    if (simpleUserRef.current && simpleUserRef.current.isConnected()) {
      if (isMuted) {
        simpleUserRef.current.unmute();
        setIsMuted(false);
      } else {
        simpleUserRef.current.mute();
        setIsMuted(true);
      }
    } else {
      setIsMuted(!isMuted); // Mock toggle
    }
  };

  const toggleHold = async () => {
    if (simpleUserRef.current && simpleUserRef.current.isConnected()) {
      try {
        if (isOnHold) {
          await simpleUserRef.current.unhold();
          setIsOnHold(false);
        } else {
          await simpleUserRef.current.hold();
          setIsOnHold(true);
        }
      } catch (e) {
        console.error(e);
      }
    } else {
      setIsOnHold(!isOnHold); // Mock toggle
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-dishhome-orange hover:bg-orange-600 text-white p-4 rounded-full shadow-lg transition-transform hover:scale-105 z-50 flex items-center justify-center"
      >
        <Phone size={24} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-80 bg-white border border-gray-200 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-sm">DishHome Softphone</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`w-2 h-2 rounded-full ${
              status === 'Registered' ? 'bg-green-500' :
              status === 'In Call' ? 'bg-red-500' :
              status === 'Connecting' ? 'bg-yellow-500' : 'bg-gray-500'
            }`}></span>
            <span className="text-xs text-gray-300">{status}</span>
          </div>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Display */}
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

      {/* Keypad */}
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

      {/* In-Call Controls */}
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
            
            <button className="flex flex-col items-center gap-1 text-gray-600">
              <div className="p-3 rounded-full bg-white shadow-sm">
                <UserPlus size={20} />
              </div>
              <span className="text-xs font-medium">Transfer</span>
            </button>
          </div>
        </div>
      )}

      {/* Action Button */}
      <div className="p-6 pt-2 flex justify-center">
        {status === 'In Call' || status === 'Ringing' ? (
          <button 
            onClick={handleHangup}
            className="w-16 h-16 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center shadow-md transition-transform hover:scale-105"
          >
            <PhoneOff size={24} />
          </button>
        ) : (
          <button 
            onClick={handleCall}
            disabled={!number}
            className={`w-16 h-16 rounded-full flex items-center justify-center shadow-md transition-transform ${
              number ? 'bg-green-500 hover:bg-green-600 text-white hover:scale-105' : 'bg-green-300 text-white cursor-not-allowed'
            }`}
          >
            <Phone size={24} />
          </button>
        )}
      </div>

      <audio ref={remoteAudioRef} autoPlay />
    </div>
  );
}
