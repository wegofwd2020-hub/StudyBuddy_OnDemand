#!/bin/sh
echo "=== what dockerd actually has open ==="                           
DPID=$(pgrep -x dockerd)                                                                                              
echo "dockerd PID = $DPID"                                              
sudo ls -la /proc/$DPID/fd/ 2>/dev/null | grep -E 'socket|sock' | head                                                
sudo cat /proc/$DPID/net/unix 2>/dev/null | grep -iE 'docker|moby' | head        
                                                                                                                        
echo                                                                             
echo "=== everything under /run that looks docker-ish ==="                                                            
sudo ls -la /run/ | grep -iE 'docker|moby|snap.docker' || echo "(nothing)"                                            
sudo find /run -maxdepth 3 -name 'docker.sock*' 2>/dev/null                                                           
sudo find /run -maxdepth 3 -name '*docker*sock*' 2>/dev/null                                                          
                                                                                                                        
echo                                                                                                                  
echo "=== leftover daemon.json (snap residue or hand-edited)? ==="                                                    
ls -la /etc/docker/ 2>&1                                                                                              
sudo cat /etc/docker/daemon.json 2>/dev/null || echo "(no /etc/docker/daemon.json)"
                                                                                                                        
echo                                                                             
echo "=== is dockerd in its own mount namespace? ==="                                                                 
readlink /proc/self/ns/mnt                                                       
sudo readlink /proc/$DPID/ns/mnt                                                                                      
# If the two readlinks differ, dockerd is in a different mount namespace from your shell
                                                                                                                        
echo                                                                             
echo "=== anything still under /run/snap.docker/? ==="                                                                
sudo ls -la /run/snap.docker/ 2>&1 | head                                        
sudo ls -la /var/snap/ 2>&1 | head                                                                                    
                                                                                                                        
echo                                                                                                                  
echo "=== try connecting at the exact path dockerd logged ==="                                                        
sudo docker -H unix:///run/docker.sock info 2>&1 | head -10

