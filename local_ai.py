import json
import urllib.error
import urllib.request


def local_ai_available(config):
    return bool(config.get('LOCAL_LLM_ENABLED') and config.get('LOCAL_LLM_BASE_URL') and config.get('LOCAL_LLM_MODEL'))


def generate_local_ai_text(config, system_prompt, user_prompt, timeout=45):
    if not local_ai_available(config):
        raise RuntimeError('Local AI is disabled.')

    endpoint = f"{config['LOCAL_LLM_BASE_URL']}/api/generate"
    prompt = f"{system_prompt.strip()}\n\nUser context:\n{user_prompt.strip()}\n\nReturn concise plain text only."
    body = json.dumps(
        {
            'model': config['LOCAL_LLM_MODEL'],
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.2,
            },
        }
    ).encode('utf-8')

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
            return (payload.get('response') or '').strip()
    except urllib.error.URLError as exc:
        raise RuntimeError(f'Local AI request failed: {exc}') from exc
