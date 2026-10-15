// Functional coverage model
covergroup motion_cg @(posedge clk);
    coverpoint position { bins low = {[0:100]}; bins mid = {[101:400]}; bins high = {[401:1000]}; }
    coverpoint velocity { bins slow = {[0:10]}; bins fast = {[11:100]}; }
endgroup
