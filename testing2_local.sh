#!/bin/sh
sudo systemctl unmask docker.socket                                                                                  
sudo systemctl enable docker.socket                                     
sudo rm -f /etc/systemd/system/docker.service.d/override.conf                                                        
sudo rmdir /etc/systemd/system/docker.service.d 2>/dev/null                      
sudo systemctl daemon-reload                                                                                         
                                                                                   
# 2. Stop everything cleanly, do NOT manually rm the socket this time                                                
sudo systemctl stop docker.service docker.socket                                 
ps -eo pid,cmd | grep -E '[d]ockerd' || echo "(dockerd stopped — good)"                                              
                                                                                                                       
# 3. Start socket → service in the right order, leave the socket file alone                                          
sudo systemctl start docker.socket                                                                                   
sleep 1                                                                                                              
ls -l /run/docker.sock        # socket should appear here BEFORE the service starts
sudo systemctl start docker.service                                                                                  
sleep 2

# 4. Verify
ls -l /var/run/docker.sock /run/docker.sock
docker info | head -15
