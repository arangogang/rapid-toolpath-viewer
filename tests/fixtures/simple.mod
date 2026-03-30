MODULE SimpleTest
  CONST robtarget p10 := [[500,0,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p20 := [[600,100,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p30 := [[700,200,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

  PROC main()
    MoveJ p10, v1000, z50, tool0;
    MoveL p20, v100, fine, tool0;
    MoveL p30, v200, z10, tool0 \WObj:=wobj0;
  ENDPROC
ENDMODULE
