import { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Pause, Play, UserPlus } from 'lucide-react';

interface SoftphoneProps {
  wsServer?: string;
  sipUri?: string;
  password?: string;
}

export function Softphone(_props: SoftphoneProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<'Disconnected' | 'Connecting' | 'Registered' | 'In Call' | 'Ringing'>('Disconnected');
  const [number, setNumber] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isOnHold, setIsOnHold] = useState(false);
  
  // SIP.js references (commented out until fully wired)
  // const userAgentRef = useRef<any>(null);
  // const sessionRef = useRef<any>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);

  // In a real implementation, you would initialize the SIP UserAgent here.
  // For the UI, we're mocking the connection states initially.
  useEffect(() => {
    // This is where we will integrate sip.js
    // const ua = new Web.SimpleUser(wsServer, { aor: sipUri });
    // ua.connect()
    
    // Mocking registration for UI purposes
    if (isOpen && status === 'Disconnected') {
      setStatus('Connecting');
      const timer = setTimeout(() => setStatus('Registered'), 1000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleDial = (digit: string) => {
    setNumber(prev => prev + digit);
  };

  const handleCall = () => {
    if (!number) return;
    setStatus('Ringing');
    // Mock call answering after 2 seconds
    setTimeout(() => {
      setStatus('In Call');
    }, 2000);
  };

  const handleHangup = () => {
    setStatus('Registered');
    setNumber('');
    setIsMuted(false);
    setIsOnHold(false);
  };

  const toggleMute = () => setIsMuted(!isMuted);
  const toggleHold = () => setIsOnHold(!isOnHold);

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
          <div className="text-sm text-gray-500 animate-pulse">00:12</div>
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
