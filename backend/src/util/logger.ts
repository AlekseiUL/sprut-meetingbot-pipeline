import { ConsoleMessage } from 'playwright';
import { createLogger, format, transports, Logger } from 'winston';
import { v5 as uuidv5, v4 } from 'uuid';
import { redact } from '../security/redact';

const NAMESPACE = uuidv5.DNS; 

export function loggerFactory(correlationId: string, botType?: string): Logger {
  return createLogger({
    format: format.combine(
      format.timestamp(),
      format((info) => {
        info.correlationId = correlationId;
        if (botType) {
          info.botType = botType;
        }
        return info;
      })(),
      format.printf(({ timestamp, level, message, correlationId, botType, ...meta }) => {
        const metaStr = Object.keys(meta).length ? JSON.stringify(redact(meta)) : '';
        const botTypeStr = botType ? ` [botType: ${botType}]` : '';
        return `[${timestamp}] [${level}] [correlationId: ${correlationId}]${botTypeStr} ${redact(message)} ${metaStr}`;
      }),
    ),
    transports: [new transports.Console()],
  });
}

export const browserLogCaptureCallback = async (logger: Logger, msg: ConsoleMessage) => {
  // Browser messages may contain meeting content and credentials. Record type only.
  logger.info('Browser console event (content omitted)', { type: msg.type() });
};

export const createCorrelationId = ({
  userId,
  eventId,
  botId,
  url,
  teamId
}: {
  userId: string,
  eventId: string | undefined,
  botId: string | undefined,
  url: string,
  teamId: string
}): string => {
  try {
    const entityId = botId ?? eventId;
    const name = `${userId}:${entityId}:${url}`;
    const id = uuidv5(name, NAMESPACE);
    console.log(`[correlationId:${id}]`);
    return id;
  } catch(err) {
    console.error('Unable to create deterministic correlationId');
    const id = v4();
    console.log(`[correlationId:${id}]`);
    return id;
  }
};

export const getErrorType = (error: unknown): string => {
  if (!error) return 'Unknown';
  
  if (error instanceof Error) {
    // Handle KnownError and its subclasses
    if (error.constructor.name === 'WaitingAtLobbyError') {
      return 'WaitingAtLobbyError';
    }
    if (error.constructor.name === 'WaitingAtLobbyRetryError') {
      return 'WaitingAtLobbyRetryError';
    }
    if (error.constructor.name === 'UnsupportedMeetingError') {
      return 'UnsupportedMeetingError';
    }
    if (error.constructor.name === 'KnownError') {
      return 'KnownError';
    }
    
    // Handle other common error types
    if (error.name === 'AxiosError' || error.constructor.name === 'AxiosError') {
      return 'AxiosError';
    }
    if (error.name === 'TimeoutError' || error.constructor.name === 'TimeoutError') {
      return 'TimeoutError';
    }
    
    // Return the constructor name for other Error instances
    return error.constructor.name || error.name || 'UnknownError';
  }
  
  return 'Unknown';
};

export class LogAggregator {
  private readonly threshold: number = 300; // 30 per minute

  private _counter: number;
  private _logger: Logger;
  private _message: string;

  constructor(logger: Logger, message: string) {
    this._counter = 0;
    this._logger = logger;
    this._message = message;
  }

  private print() {
    this._logger.info(`${this._counter} logs printed for: ${this._message}`);
  }

  public log() {
    this._counter += 1;
    if (this._counter >= this.threshold) {
      this.print();
      this._counter = 0;
    }
  }

  public flush() {
    if (this._counter > 0) {
      this.print();
      this._counter = 0;
    }
  }
}

export const getCorrelationIdLog = (correlationId: string) => {
  return `[correlationId: ${correlationId || 'None'}]`;
};
