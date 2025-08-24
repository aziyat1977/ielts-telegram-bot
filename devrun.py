import uvicorn, os
if __name__ == '__main__':
    uvicorn.run('app.mux_main:app', host='0.0.0.0', port=int(os.getenv('PORT','8080')),
                proxy_headers=True, forwarded_allow_ips='*')
